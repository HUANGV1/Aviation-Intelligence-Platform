# Aviation Intelligence AI Platform

## Current Architecture Direction

The project is pivoting from a split-pane document Q&A console to a **single agent chat interface**.

Current implementation status:

| Area | Status |
|------|--------|
| Agent chat API (`POST /agent/chat`) | Implemented |
| Internal tool registry | Implemented |
| `document_search` tool over cited RAG | Implemented |
| Legacy `/rag/*` endpoints | Preserved |
| Aviation API tools (METAR, TAF, NOTAM, etc.) | Planned |
| MCP adapter layer | Planned |
| Conversation memory | Planned |
| Hybrid retrieval and reranking | Planned |
| Observability dashboard | Planned |
| Evaluation pipeline | Planned |

See:

- [`docs/AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md)
- [`docs/PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md)

## 1. Project Summary

The Aviation Intelligence AI Platform is an AI-powered operations and safety intelligence system for aviation data. The platform helps users ingest, search, summarize, and reason over aviation documents and operational data such as accident reports, FAA documents, weather, NOTAMs, and incident records.

The project should feel like an enterprise aviation operations platform, not a generic chatbot. The ideal demo is a polished system where a user can upload aviation documents, ask cited questions, generate airport briefings, and eventually combine multiple aviation data sources through AI workflows.

The main goal is to demonstrate strong software engineering and modern AI engineering skills:

- Retrieval-Augmented Generation, or RAG
- document ingestion pipelines
- vector databases
- backend architecture
- typed APIs
- async processing
- real-world data integration
- AI workflow orchestration
- polished frontend dashboards
- production-style engineering practices

## 2. Product Vision

The long-term vision is an aviation operations intelligence platform that supports analysts, students, operators, safety researchers, and engineers who need to quickly understand aviation conditions, incidents, procedures, and risks.

Users should be able to ask questions such as:

- "What caused the hydraulic failure in this NTSB report?"
- "Brief me on weather conditions affecting YYZ tomorrow morning."
- "Show recent incidents involving runway excursions in poor visibility."
- "Generate a briefing for JFK operations tomorrow morning."
- "What FAA guidance applies to runway incursion prevention?"

The system should retrieve relevant aviation data, cite its sources, summarize findings, and produce concise operational briefings.

## 3. Target Users

Primary portfolio/demo users:

- software engineering recruiters
- AI/ML recruiters
- aerospace and defense companies
- technical interviewers
- other engineers reviewing the project

Product-style users:

- aviation safety analysts
- airport operations analysts
- dispatch-style operations users
- aviation students and researchers
- maintenance or compliance researchers

## 4. Core Product Principles

The project should follow these principles:

- Be useful before it is large.
- Build one strong end-to-end workflow before adding more data sources.
- Prioritize citations, traceability, and source quality.
- Treat AI output as explainable intelligence, not magic.
- Make the UI feel like an operations tool, not a chatbot clone.
- Keep infrastructure free or low-cost wherever possible.
- Prefer simple architecture that can be explained clearly in interviews.

## 5. MVP Scope

The MVP should prove the core idea with a focused, demoable workflow:

> Upload aviation documents, ask questions, retrieve relevant chunks, and generate cited answers in a simple professional UI.

The MVP should include:

- PDF document upload
- aviation document metadata storage
- PDF text extraction
- text chunking
- embeddings generation
- vector search
- RAG answer generation
- citations and source snippets
- simple document library UI
- simple chat/question interface
- backend API
- Supabase database (hosted PostgreSQL + pgvector)
- local app development (frontend + backend run locally; database on Supabase)
- README and architecture documentation

The MVP should not include:

- live flight tracking
- maps
- user accounts
- payments
- Kubernetes
- complex agent frameworks
- real-time alerts
- anomaly detection
- large-scale scraping
- multiple LLM providers

## 6. MVP User Stories

### Document Upload

As a user, I want to upload an aviation PDF so that I can ask questions about it.

Acceptance criteria:

- user can upload a PDF from the frontend
- backend stores the file or file reference
- backend creates a document record
- UI shows uploaded documents
- upload status is visible

### Document Processing

As a user, I want the system to process my document so that it becomes searchable.

Acceptance criteria:

- backend extracts text from the PDF
- backend splits text into chunks
- chunks are stored with document metadata
- page numbers or source references are stored when available
- document status changes from uploaded to processed

### Semantic Search

As a user, I want to search across aviation documents using natural language.

Acceptance criteria:

- user enters a query
- backend embeds the query
- vector search returns relevant chunks
- UI displays source snippets

### Cited AI Answering

As a user, I want an AI-generated answer with citations so that I can trust the response.

Acceptance criteria:

- backend retrieves relevant chunks
- LLM generates a concise answer
- answer includes citations to source chunks
- UI displays cited snippets below or beside the answer
- answer does not invent unsupported facts

## 7. MVP Demo Flow

The final MVP demo should look like this:

1. User opens the app.
2. User uploads an NTSB accident report or FAA advisory circular.
3. App processes the document.
4. User asks: "What were the contributing factors in this report?"
5. App retrieves relevant chunks.
6. App returns a cited summary.
7. User opens the source citations and sees supporting snippets.

This is the smallest strong demo because it proves ingestion, retrieval, AI generation, citations, backend design, and frontend usability.

## 8. Recommended Free Or Low-Cost Tech Stack

### Frontend

Recommended:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Query or TanStack Query

Why:

- free and widely used
- looks professional quickly
- TypeScript improves engineering quality
- easy to deploy later on Vercel

### Backend

Recommended:

- FastAPI
- Python
- Pydantic
- SQLAlchemy or SQLModel
- Alembic for migrations

Why:

- strong fit for AI/data work
- clean API development
- good async support
- easy integration with PDF, embedding, and data libraries

Alternative:

- NestJS if you prefer a TypeScript-only stack

### Database

Recommended:

- Supabase (hosted PostgreSQL)
- pgvector extension (enabled in Supabase SQL Editor)

Why:

- free tier is enough for MVP
- no local Postgres or extension install required
- stores normal relational data and vector embeddings together
- same SQLAlchemy + pgvector stack as production
- optional Supabase Storage later for uploaded PDFs

### File Storage

MVP:

- local filesystem storage

Post-MVP:

- Supabase Storage free tier
- Cloudflare R2 free/low-cost tier
- S3-compatible storage

### Embeddings

Free/local option:

- sentence-transformers
- all-MiniLM-L6-v2
- bge-small-en

Paid but simple option:

- OpenAI embeddings

Recommendation:

- Start with local embeddings if you want to minimize cost.
- Use OpenAI embeddings if you want faster setup and more consistent quality.

### LLM

Free/local options:

- Ollama
- Llama 3.x models
- Mistral models
- Qwen models

Paid but easier options:

- OpenAI
- Anthropic
- Google Gemini

Recommendation:

- Design an `LLMService` wrapper so you can switch providers.
- For a portfolio project, it is acceptable to use a paid API during development if usage is low.
- If cost is a priority, use Ollama locally for development and keep the provider interface flexible.

### PDF Processing

Recommended:

- pypdf
- pdfplumber

Possible later:

- unstructured
- pymupdf

Recommendation:

- Start with `pypdf` or `pdfplumber`.
- Add more advanced parsing only if simple extraction is not enough.

### Background Jobs

MVP:

- FastAPI background tasks

Post-MVP:

- Celery + Redis
- RQ + Redis
- Arq

Recommendation:

- Start simple.
- Add a proper queue when processing becomes slow or unreliable.

### Local Development

Recommended:

- run frontend and backend locally
- use Supabase free tier for PostgreSQL + pgvector

Services:

- frontend (local)
- backend (local)
- database (Supabase cloud)

### Testing

Frontend:

- Vitest
- React Testing Library

Backend:

- pytest
- httpx test client

AI/RAG evaluation:

- small hand-written evaluation set in JSON or YAML
- questions with expected source documents/chunks

### Deployment

Free or low-cost options:

- frontend on Vercel free tier
- backend on Render free tier, Railway, Fly.io, or similar
- database on Supabase free tier

Recommendation:

- use Supabase from day one for the MVP database
- deploy frontend/backend after the core RAG workflow works locally

## 9. Proposed Architecture

High-level architecture:

```text
Frontend UI
  |
  | HTTP/JSON
  v
FastAPI Backend
  |
  |-- Document Service
  |-- Ingestion Service
  |-- Chunking Service
  |-- Embedding Service
  |-- Retrieval Service
  |-- LLM Service
  |-- Citation Service
  |
  v
Supabase PostgreSQL + pgvector
  |
  |-- documents
  |-- document_chunks
  |-- rag_queries
  |-- citations
```

Recommended repository structure:

```text
aviation-intelligence/
  apps/
    frontend/
    backend/
  docs/
    project-spec.md
    architecture.md
    rag-design.md
    SUPABASE_SETUP.md
  infra/
    init-db.sql
  README.md
```

Backend structure:

```text
apps/backend/
  app/
    api/
    core/
    db/
    models/
    services/
      documents.py
      ingestion.py
      chunking.py
      embeddings.py
      retrieval.py
      llm.py
      citations.py
    tests/
```

Frontend structure:

```text
apps/frontend/
  app/
  components/
  lib/
  features/
    documents/
    rag/
    briefings/
```

## 10. MVP Data Model

### documents

Stores uploaded document metadata.

Suggested fields:

- id
- filename
- original_filename
- source_type
- status
- file_path
- page_count
- created_at
- updated_at

### document_chunks

Stores extracted chunks and embeddings.

Suggested fields:

- id
- document_id
- chunk_index
- text
- page_number
- section_title
- token_count
- embedding
- created_at

### rag_queries

Stores user questions and generated answers for debugging and demos.

Suggested fields:

- id
- query
- answer
- document_id
- retrieved_chunk_ids
- created_at

## 11. MVP API Endpoints

Suggested backend endpoints:

```text
GET  /health
POST /documents/upload
GET  /documents
GET  /documents/{document_id}
POST /documents/{document_id}/process
GET  /documents/{document_id}/chunks
POST /rag/query
```

Example RAG request:

```json
{
  "document_id": "uuid",
  "query": "What were the contributing factors in this accident?"
}
```

Example RAG response:

```json
{
  "answer": "The report identifies poor visibility, delayed braking, and insufficient runway awareness as key contributing factors.",
  "citations": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "page_number": 12,
      "snippet": "The aircraft touched down long during low visibility conditions..."
    }
  ]
}
```

## 12. RAG Design

The RAG pipeline should be simple and explainable.

Pipeline:

1. Extract text from PDF.
2. Split text into chunks.
3. Generate embeddings for each chunk.
4. Store chunks and embeddings in Supabase pgvector.
5. Embed the user's query.
6. Retrieve top-k similar chunks.
7. Build a prompt using retrieved chunks.
8. Generate answer.
9. Return answer with citations.

Initial chunking strategy:

- 500-1,000 tokens per chunk
- 100-150 token overlap
- preserve page number when possible
- store section title if available

Retrieval strategy:

- top 5-8 chunks for MVP
- order by vector similarity
- include source metadata in the prompt

Hallucination mitigation:

- instruct the model to answer only from retrieved sources
- tell the model to say when evidence is insufficient
- always show citations
- include source snippets in the UI
- avoid unsupported operational recommendations

## 13. Prompting Approach

System behavior:

- Be concise.
- Use only provided sources.
- Cite claims.
- If sources are insufficient, say so.
- Do not invent aviation facts.
- Prefer safety-conscious language.

Example prompt structure:

```text
You are an aviation safety research assistant.
Answer the user's question using only the provided source excerpts.
If the excerpts do not contain enough information, say that the available sources are insufficient.
Include citations using the provided source IDs.

User question:
{question}

Sources:
{retrieved_chunks}
```

## 14. MVP Build Plan

### Phase 1: Project Setup

Deliverables:

- GitHub repository
- monorepo structure
- frontend app
- backend app
- Supabase PostgreSQL + pgvector
- backend health endpoint
- basic README
- Supabase setup guide

Definition of done:

- backend and frontend run locally
- frontend can call backend health endpoint
- backend can connect to Supabase database

### Phase 2: Document Upload

Deliverables:

- upload API
- local file storage
- documents table
- document list UI

Definition of done:

- user can upload a PDF
- document appears in UI
- metadata is stored in database

### Phase 3: Text Extraction And Chunking

Deliverables:

- PDF text extraction
- chunking service
- document_chunks table
- document processing status

Definition of done:

- uploaded PDF is processed into chunks
- chunks can be viewed or inspected
- processing failures are handled cleanly

### Phase 4: Embeddings And Vector Search

Deliverables:

- embedding service
- pgvector storage in Supabase
- query embedding
- semantic search endpoint

Definition of done:

- user can enter a query
- backend returns relevant chunks

### Phase 5: RAG Answering

Deliverables:

- LLM service
- RAG query endpoint
- citation formatting
- answer UI
- source snippet panel

Definition of done:

- user asks a question
- app returns cited answer
- user can inspect the supporting snippets

### Phase 6: MVP Polish

Deliverables:

- loading states
- error states
- sample aviation documents
- screenshots
- README demo instructions
- basic tests
- small RAG evaluation set

Definition of done:

- another engineer can clone, run, and understand the project
- demo works reliably with at least one aviation PDF

## 15. Suggested 3-Month Roadmap

### Month 1: Core RAG MVP

Focus:

- project setup
- document upload
- PDF processing
- chunking
- embeddings
- vector search
- cited RAG answers

End-of-month target:

- upload an aviation PDF and ask cited questions about it

### Month 2: Aviation Operations Data

Focus:

- airport weather integration
- METAR and TAF summaries
- simple airport briefing generator
- incident dataset ingestion
- operational summary UI

End-of-month target:

- generate a basic airport briefing using weather plus document intelligence

### Month 3: Product Polish And Intelligence Layer

Focus:

- improved dashboard
- briefing workflow
- source trace panel
- RAG evaluation
- incident search
- deployment
- README and portfolio packaging

End-of-month target:

- polished deployed demo with screenshots, architecture docs, and sample workflows

## 16. Post-MVP Features

### Airport Briefing Generator

Users enter an airport code and time window.

The system returns:

- METAR summary
- TAF forecast summary
- operational weather risks
- NOTAM summary
- relevant document guidance
- source timestamps

Example:

```text
Generate a briefing for JFK tomorrow morning.
```

### Weather Integration

Potential sources:

- NOAA Aviation Weather Center
- METAR/TAF feeds
- AviationWeather.gov APIs

Features:

- airport weather page
- wind/visibility/ceiling summaries
- operational risk labels
- route weather summary

### NOTAM Processing

Features:

- ingest NOTAM text
- classify NOTAM type
- summarize plain-English impact
- identify runway/taxiway/airspace relevance
- include notices in airport briefing

Possible categories:

- runway closure
- taxiway closure
- lighting issue
- navigation aid outage
- airspace restriction
- procedure change
- construction

### Incident And Safety Intelligence

Potential sources:

- NTSB reports
- NTSB accident database
- Aviation Safety Network
- FAA safety documents

Features:

- incident search
- semantic incident matching
- cause/factor extraction
- similar incident clustering
- trend summaries

Example:

```text
Find incidents involving runway excursions in poor visibility.
```

### AI Briefing Workflow

A workflow engine can combine multiple systems:

1. Parse user request.
2. Identify airport, route, aircraft, or time window.
3. Fetch weather.
4. Fetch notices.
5. Retrieve relevant documents.
6. Search incident history.
7. Generate final briefing.
8. Show source trace.

This does not need a complex agent framework at first. A deterministic workflow is easier to build, test, and explain.

### Flight Tracking

Potential sources:

- OpenSky Network
- ADS-B Exchange, if access is available

Features:

- aircraft positions
- route visualization
- altitude and speed
- historical flight replay
- event detection

Recommendation:

- Add this after the briefing and RAG system are solid.
- Maps and live tracking are visually impressive but can consume a lot of time.

### Maps And Dashboard

Possible tools:

- Leaflet
- MapLibre
- Mapbox free tier

Features:

- airport map
- route map
- aircraft positions
- weather overlays
- incident locations

### Advanced AI Features

Possible ideas:

- hybrid search with keyword plus vector retrieval
- reranking retrieved chunks
- automatic document summaries
- entity extraction for aircraft, airports, dates, and causes
- incident clustering
- anomaly detection
- trend prediction
- briefing templates
- evaluation dashboard

### Enterprise-Style Features

Possible ideas:

- user accounts
- saved briefings
- audit logs
- data source freshness monitoring
- admin ingestion dashboard
- role-based access
- API keys
- organization workspaces

## 17. Data Sources And Acquisition Strategy

Sources enter the platform through four acquisition modes. The right mix depends on the phase: MVP should stay upload-first; post-MVP adds curated seed data and selective automated pulls.

### How Sources Get Into The System

```text
                    ┌─────────────────────────────────────┐
                    │         Unified Source Layer         │
                    │  (documents, weather, NOTAMs, etc.)  │
                    └─────────────────────────────────────┘
                                        ▲
          ┌─────────────────────────────┼─────────────────────────────┐
          │                             │                             │
   User Upload                   Curated Seed              Automated Pull
   (MVP primary)                 (demo + baseline)         (post-MVP)
          │                             │                             │
   PDF via UI                   Bundled sample PDFs        On-demand API fetch
   optional URL paste           NTSB/FAA starter set       Scheduled sync jobs
```

#### 1. User Upload (MVP — primary)

The user brings the document. This is the right default for Month 1.

- **What:** PDF upload through the document library UI; optional URL paste later.
- **Best for:** NTSB reports, FAA advisory circulars, internal SOPs, training material, one-off investigations.
- **Why start here:** Proves ingestion → chunking → RAG → citations without API keys, scraping, or licensing risk. Matches how analysts actually work — they often have a specific report or circular in hand.
- **Limitation:** Empty library on first visit unless you also ship seed data (see below).

#### 2. Curated Seed Data (MVP polish — strongly recommended)

The project ships with a small, hand-picked document set so the demo works out of the box.

- **What:** 3–10 public-domain aviation PDFs checked into `sample-data/` or loaded via a one-time seed script.
- **Good candidates:** One NTSB accident report, one FAA advisory circular (e.g. runway incursion prevention), one handbook excerpt.
- **Why:** Recruiters and interviewers can run the demo without hunting for files. Shows you thought about onboarding, not just the happy path where the user already has documents.
- **Not scraping:** You download these once, verify licensing, and bundle them. This is curation, not a live pipeline.

#### 3. On-Demand Fetch (Month 2+ — best first automation)

The system pulls a source when the user asks for something specific, not on a schedule.

- **What:** User says "Brief me on KJFK tomorrow" → backend calls AviationWeather.gov for METAR/TAF, FAA NOTAM API or a fallback sample, then optionally retrieves matching chunks from the document index.
- **Best for:** Weather, NOTAMs, live operational data — things that must be fresh at query time.
- **Why before scheduled sync:** Simpler to build and explain. No background workers, no stale-data reconciliation, no cron. The briefing workflow in Section 16 already fits this model.
- **Pattern:** Fetch → normalize to text/JSON → optionally cache with TTL → pass to LLM with timestamp and source URL in citations.

#### 4. Scheduled Sync (Month 3+ — selective, not bulk scraping)

Background jobs periodically ingest or refresh datasets.

- **What:** Nightly job pulls new NTSB reports, refreshes an incident index, or re-fetches NOTAM archives for airports in a watchlist.
- **Best for:** Large public catalogs (NTSB docket search, FAA document libraries), incident trend analysis, "what's new since last week" features.
- **When to add:** After on-demand fetch works and you have a real need for historical search across many documents — not for MVP.
- **Keep it narrow:** Sync one source well (e.g. NTSB CAROL query API or a static CSV export) rather than building a generic scraper. Section 5 explicitly excludes "large-scale scraping" from MVP scope.

### Recommended Phasing

| Phase | Acquisition mode | Example |
|-------|------------------|---------|
| MVP (Month 1) | User upload + curated seed | Upload one PDF; demo also ships with a sample NTSB report |
| Month 2 | On-demand API fetch | Airport briefing pulls live METAR/TAF when user requests a briefing |
| Month 3 | Scheduled sync (optional) | Weekly NTSB ingest for incident search; freshness badge in UI |
| Enterprise (later) | Admin ingestion dashboard | Ops team configures sources, sync frequency, and access rules |

### Should The System Pull Sources Automatically?

**Yes, but not at MVP, and not for everything.**

| Source type | User upload? | On-demand pull? | Scheduled sync? | Notes |
|-------------|--------------|-----------------|-----------------|-------|
| PDF documents (NTSB, FAA ACs) | Primary | Optional (URL → download) | Later, if building incident corpus | Upload + seed is enough for portfolio demo |
| Weather (METAR/TAF) | No | **Yes — required** | Cache only (short TTL) | Must be fresh at query time; never expect users to upload METARs |
| NOTAMs | No | **Yes** | Optional refresh | API access can be awkward; sample NOTAMs OK for demo with clear disclaimer |
| Incident databases | Seed CSV/PDF first | Search API on query | Weekly bulk ingest | Start with bundled reports; add NTSB search when incident features ship |
| Flight data (OpenSky) | No | Yes (live query) | No | Real-time only; maps/tracking are post-MVP |

**Principles:**

1. **Documents = upload or curated seed first.** Users and demos need control and traceability. Automated PDF ingestion is a Month 3 feature, not a Month 1 requirement.
2. **Operational data = pull on demand.** Weather and NOTAMs are useless if uploaded manually. Fetch when the user asks; show `retrieved_at` in citations.
3. **Scheduled sync only where history matters.** Incident trends and "new reports this week" justify background jobs. Do not sync everything on a cron — that adds ops burden and stale-data edge cases for little MVP value.
4. **Always cite provenance.** Every chunk or API response should carry: `source_type`, `source_url` or `filename`, `retrieved_at` or `uploaded_at`, and `document_id` / external id where applicable. This aligns with Section 4 (traceability).

### Source Metadata Model (extend MVP)

When adding pulled sources, extend the `documents` table (or add a `sources` table) with:

- `acquisition_mode`: `upload` | `seed` | `fetch` | `sync`
- `source_url`: original URL if fetched
- `retrieved_at`: when an API pull happened
- `expires_at`: optional TTL for cached operational data
- `external_id`: e.g. NTSB report number, NOTAM id, METAR station + obs time

Operational API responses may never become full PDFs — store them as structured records or short-lived text blobs linked to briefings, with the same citation pipeline as document chunks.

### Aviation Documents

Possible sources:

- FAA advisory circulars
- FAA handbooks
- FAA safety documents
- NTSB accident reports
- aircraft manuals where legally available
- safety bulletins
- public operating procedures

### Weather

Possible sources:

- AviationWeather.gov
- NOAA Aviation Weather Center
- METAR feeds
- TAF feeds

### NOTAMs

Possible sources:

- FAA NOTAM Search
- public NOTAM examples
- static sample datasets for MVP-style demos

Note:

- NOTAM access can be annoying depending on API availability.
- It is acceptable to start with sample NOTAM data as long as the project explains the limitation.

### Incidents

Possible sources:

- NTSB accident reports
- NTSB accident database
- public aviation safety datasets
- Aviation Safety Network, depending on usage permissions

### Flight Data

Possible sources:

- OpenSky Network
- ADS-B Exchange, if access is available

## 18. Engineering Quality Checklist

Backend:

- typed request and response models
- clean service boundaries
- database migrations
- environment variables
- error handling
- structured logs
- tests for chunking and retrieval
- health endpoint

Frontend:

- professional layout
- responsive design
- loading states
- error states
- source citation display
- document upload progress
- clean navigation

AI:

- citations
- source snippets
- retrieval evaluation
- prompt versioning
- insufficient-evidence behavior
- no unsupported claims

DevOps:

- README setup instructions
- Supabase setup guide (`docs/SUPABASE_SETUP.md`)
- `.env.example`
- CI checks
- deployment notes

Documentation:

- project spec
- architecture diagram
- RAG design notes
- data source limitations
- sample demo script
- future roadmap

## 19. Portfolio Presentation

The project README should eventually include:

- one-sentence product pitch
- screenshots or GIFs
- quickstart instructions
- architecture diagram
- RAG pipeline explanation
- data sources
- example questions
- example answers with citations
- limitations
- roadmap

Suggested pitch:

> Aviation Intelligence is an AI-powered aviation operations platform that ingests aviation documents and operational data to generate cited safety answers and airport briefings.

Suggested demo questions:

- "What were the contributing factors in this accident report?"
- "Summarize the key safety recommendations."
- "What evidence supports the conclusion?"
- "What operational risks are present for this airport?"
- "Find similar runway excursion incidents."

## 20. Recommended Starting Point

Start with the smallest valuable version:

1. Create the repo.
2. Write the README and MVP scope.
3. Set up FastAPI, Next.js, and Supabase with pgvector.
4. Upload one PDF.
5. Extract text.
6. Chunk it.
7. Store embeddings.
8. Ask one question.
9. Return one cited answer.

Do not start with flight tracking, maps, or agents. The first milestone should be a working aviation document intelligence system. Once that is strong, add airport briefings and operational data.

