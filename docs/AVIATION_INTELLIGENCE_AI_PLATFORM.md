# Aviation Intelligence AI Platform

Product vision and current system overview for the Aviation Intelligence Platform portfolio project.

Related docs:

- [`../README.md`](../README.md) — quick start and feature summary
- [`AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md) — agent, tools, trust boundaries
- [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md) — database setup

---

## Current status

The app is an **agent-first** local portfolio MVP: one chat interface that can answer directly, search uploaded PDFs with citations, or call operational aviation tools.

| Area | Status |
|------|--------|
| Agent chat (`POST /agent/chat`) | Implemented |
| Typed tool registry | Implemented |
| `document_search` over cited RAG | Implemented |
| METAR / TAF / international SIGMETs | Implemented (AviationWeather.gov) |
| NOTAMs | Implemented (demo fixtures) |
| Conversation memory + session sidebar | Implemented |
| Document library (upload / process / preview) | Implemented |
| Legacy `/rag/*` APIs | Preserved |
| End-user auth / multi-tenant ownership | Not implemented (localhost demo) |
| MCP adapter | Planned |
| Hybrid retrieval + reranking | Planned |
| Observability / eval harness | Planned |
| Public deployment hardening | Planned |

---

## 1. Project summary

Aviation Intelligence is an AI-powered operations and safety intelligence system for aviation data. Users ingest PDFs (NTSB reports, FAA guidance, and similar), ask natural-language questions, and get **cited answers** or **live operational summaries** (weather, forecasts, SIGMETs, demo NOTAMs) from one assistant.

It is meant to feel like a focused operations tool, not a generic chatbot wrapper. The portfolio goal is to demonstrate:

- Retrieval-Augmented Generation (RAG)
- Document ingestion pipelines
- Vector search with pgvector
- LLM tool orchestration
- Typed APIs and clean service boundaries
- Real-world aviation API integration
- Polished product UI

---

## 2. Product vision

Long-term: help analysts, students, operators, and researchers understand aviation conditions, incidents, procedures, and risks quickly.

Example questions the product aims to support:

- "What caused the hydraulic failure in this NTSB report?"
- "What FAA guidance applies to runway incursion prevention?"
- "What's the current METAR for KJFK?"
- "Give me the TAF for KLAX and any active NOTAMs."
- "Generate a briefing for JFK operations tomorrow morning."

The system should retrieve relevant data, cite sources, summarize findings, and keep provenance visible.

---

## 3. Target users

**Portfolio / demo audience**

- Software and AI/ML recruiters
- Aerospace and defense technical interviewers
- Engineers reviewing the codebase

**Product-style users (vision)**

- Aviation safety and airport operations analysts
- Dispatch-style operations users
- Aviation students and researchers

---

## 4. Product principles

- Be useful before it is large
- Prefer one strong end-to-end workflow over many half-built sources
- Prioritize citations, traceability, and source quality
- Treat AI output as explainable intelligence, not magic
- Keep the UI operations-oriented, not a chatbot clone
- Prefer simple architecture that is easy to explain in interviews
- Keep infrastructure free or low-cost for local demos

---

## 5. What shipped

### Capabilities

- PDF upload with validation (extension, size, `%PDF` magic bytes)
- Extract → page-aware chunk → embed → store in Supabase pgvector
- Semantic search and cited RAG answers with insufficient-evidence handling
- Agent chat with multi-tool turns (documents + operational tools)
- Persistent chat sessions with recent-turn memory
- Document-scoped chat (UI `document_id` overrides model tool args)
- Operational tools with `retrieved_at`, provider, and source URL
- Frontend workspace: chat, sessions, library, citations, tool activity, markdown answers

### Demo flow

1. Open the app at `http://localhost:3000`
2. Upload an aviation PDF and process it
3. Optionally attach/scope that document in chat
4. Ask a document question → cited answer with snippets
5. Ask for METAR/TAF/NOTAMs/SIGMETs → tool activity + operational sources
6. Continue the thread; session history persists

### Out of scope for this MVP

- User accounts, payments, multi-tenant auth
- Live flight tracking / maps
- Kubernetes / complex agent frameworks
- Real-time alerts, anomaly detection
- Large-scale scraping
- Multiple LLM providers in production config (Gemini is the current provider)

---

## 6. Tech stack (as built)

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4, react-markdown |
| Backend | FastAPI, Python 3.12+, Pydantic Settings, SQLAlchemy, httpx |
| Database | Supabase PostgreSQL + pgvector (HNSW cosine index, 768-dim) |
| AI | Google Gemini (embeddings, agent turns, cited JSON answers) |
| PDF | pypdf, pdfplumber |
| File storage | Local `uploads/` directory |
| Ops weather | AviationWeather.gov (public) |
| Ops NOTAMs | Local demo JSON fixtures |

Local development: frontend + backend on the machine; database on Supabase free tier.

---

## 7. Architecture

```text
Next.js workspace
  |
  | HTTP/JSON
  v
FastAPI
  |-- Agent service (tool loop + session memory)
  |-- Tool registry
  |     |-- document_search → RAG (search + cited answer)
  |     |-- get_metar / get_taf / get_international_sigmets
  |     |-- get_notams (demo)
  |-- Document upload / process / storage
  |-- Embedding + LLM services (Gemini)
  v
Supabase PostgreSQL + pgvector
  |-- documents
  |-- document_chunks
  |-- rag_queries
  |-- chat_sessions
  |-- chat_messages
```

Repository layout:

```text
apps/frontend/          Next.js UI
apps/backend/app/       FastAPI app (api, services, tools, schemas)
docs/                   Product + architecture + Supabase setup
infra/init-db.sql       Schema bootstrap
sample-data/            Small test PDFs
```

Details: [`AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md)

---

## 8. Data model

### `documents`

Uploaded PDF metadata: `id`, `filename`, `original_filename`, `source_type`, `acquisition_mode`, `status`, `file_path`, `page_count`, `source_url`, timestamps.

### `document_chunks`

Chunk text + `embedding vector(768)`, `page_number`, `section_title`, `token_count`, `chunk_index`.

### `rag_queries`

Optional audit/history for direct `/rag/query` calls (agent path uses `persist=False`).

### `chat_sessions` / `chat_messages`

Persistent agent conversations: titles, optional `document_id`, roles, content, citations JSON, operational sources JSON, tool activity, flags.

Full DDL: [`../infra/init-db.sql`](../infra/init-db.sql)

---

## 9. API surface

```text
GET    /health
POST   /agent/chat
POST   /agent/sessions
GET    /agent/sessions
GET    /agent/sessions/{id}
DELETE /agent/sessions/{id}
POST   /documents/upload
GET    /documents
GET    /documents/{id}
GET    /documents/{id}/file
POST   /documents/{id}/process
POST   /documents/{id}/cancel
GET    /documents/{id}/chunks
DELETE /documents/{id}
POST   /rag/query
POST   /rag/search
```

Interactive schemas: `http://localhost:8000/docs` when the backend is running.

---

## 10. RAG design

Pipeline:

1. Extract PDF text (page-aware when possible)
2. Chunk with overlap; store page metadata
3. Embed chunks (Gemini, 768 dimensions)
4. Store in pgvector with HNSW index
5. Embed the user query
6. Retrieve top-k by cosine similarity
7. Filter by minimum similarity
8. Grounded JSON generation
9. Validate citations; downgrade when evidence is insufficient

Hallucination mitigations:

- Answer from retrieved sources only for document claims
- Explicit insufficient-evidence path
- Show citations and snippets in the UI
- Agent must call `document_search` before claiming document evidence

---

## 11. Trust boundaries

| Capability | Source of truth |
|------------|-----------------|
| Document citations | `document_search` / RAG only |
| Live METAR / TAF / SIGMET | Operational tools only |
| NOTAMs | Demo tool only (fixture data) |
| General aviation knowledge | Direct agent answer (no fake citations) |
| Ops freshness | `retrieved_at` on operational bundles |
| Scoped document chat | Request `document_id` overrides model args |

---

## 12. Data sources and acquisition

| Source type | How it enters today | Notes |
|-------------|---------------------|-------|
| Aviation PDFs | User upload | Primary document path |
| Sample PDFs | `sample-data/` | Local testing helpers |
| METAR / TAF / SIGMET | On-demand API fetch | AviationWeather.gov |
| NOTAMs | Demo JSON fixture | Swap for a live provider later |

**Principles**

1. Documents = upload first (control + traceability)
2. Operational data = pull on demand when the user asks
3. Always surface provenance (`provider`, `source_url`, `retrieved_at` / filename)
4. Prefer narrow, explainable integrations over bulk scraping

Possible later sources: FAA advisory libraries, NTSB corpuses, live NOTAM APIs, OpenSky flight data, maps.

---

## 13. Future direction

Ideas beyond the current MVP (not required for the portfolio demo):

- Authentication, per-user document/session ownership, rate limits
- MCP adapter for external tool servers
- Hybrid search (vector + keyword) and reranking
- Richer airport briefing workflow combining docs + ops tools
- Live NOTAM provider
- Observability dashboard and evaluation datasets
- Object storage for PDFs (Supabase Storage / S3)
- Optional maps / flight tracking (high effort; add only after core stays solid)

---

## 14. Engineering quality checklist

**Backend:** typed Pydantic models, service boundaries, parameterized SQL, env-based config, health endpoint, pytest coverage for chunking/RAG/tools/agent paths.

**Frontend:** workspace layout, loading/error states, citations, tool activity, document upload/process UX, markdown answers.

**AI:** citations, insufficient-evidence behavior, tool trust boundaries, bounded tool rounds, server-side only secrets.

**Docs / ops:** README quick start, Supabase guide, `.env.example` files, schema in `infra/init-db.sql`.

**Hosting note:** The API has no end-user auth today. Keep it on localhost (or behind a private gate) until auth, tenancy, and rate limits exist.

---

## 15. Portfolio presentation

Suggested pitch:

> Aviation Intelligence is an agent-first aviation ops assistant that turns uploaded PDFs into cited answers and can pull live weather and forecasts through typed tools—with provenance visible in the UI.

README should include (and largely does): one-line pitch, architecture diagram, quick start, tool table, example questions, limitations, and links to these docs.

Suggested live demo script:

1. Health indicators green
2. Process a sample/accident PDF
3. Ask a cited document question with scope attached
4. Ask for METAR + TAF for an airport
5. Show tool activity and operational source timestamps
6. Reopen the chat from the session sidebar
