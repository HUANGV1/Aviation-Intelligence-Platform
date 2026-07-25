# Aviation Intelligence Platform

Upload aviation PDFs, chat with an aviation intelligence agent, and get cited answers from your document library or direct agent responses.

## Features

- **Agent chat** — one interface where the assistant decides whether to answer directly or use tools
- **Conversation memory** — persistent chat sessions with recall of recent turns for follow-up questions
- **Chat session management** — new, reopen, continue, and delete chats from a collapsible sidebar
- **Document search tool** — cited answers from uploaded PDFs with source validation
- **Live operational tools** — METAR, TAF, and international SIGMETs (AviationWeather.gov)
- **Document library** — upload PDFs, process them for search, and manage your collection
- **Legacy RAG APIs** — `/rag/query` and `/rag/search` remain available for compatibility
- **Health monitoring** — frontend and API report backend and database connectivity

## Architecture

The platform is moving from a split-pane RAG console to an agent-first design:

- Frontend chat shell calls `POST /agent/chat`
- Backend agent orchestrator uses Gemini tool calling
- `document_search` wraps the existing cited RAG pipeline
- Operational aviation API tools register into the same tool layer with provenance metadata

See:

- [`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md)
- [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md)

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12+ |
| Database | Supabase (PostgreSQL + pgvector) |
| AI | Google Gemini (embeddings, agent turns, cited answers) |

## Prerequisites

- Git
- Node.js 22+
- Python 3.12+
- A [Supabase](https://supabase.com) project
- A Google Gemini API key

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/HUANGV1/Aviation-Intelligence-Platform.git
cd Aviation-Intelligence-Platform
```

2. Set up Supabase — follow [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md) to create a project, enable pgvector, and run the schema from `infra/init-db.sql`.

3. Copy environment files:

```bash
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.local.example apps/frontend/.env.local
```

4. Fill in `apps/backend/.env` with your Supabase credentials and `GEMINI_API_KEY`. Adjust other settings as needed (see [Environment Variables](#environment-variables)).

5. Start the backend (terminal 1):

```bash
cd apps/backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

6. Start the frontend (terminal 2):

```bash
cd apps/frontend
npm install
npm run dev
```

7. Open the app:

- Frontend: http://localhost:3000
- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

Upload a PDF from the document library, process it, then ask the agent a question in the chat panel.

## Project Structure

```text
apps/
  frontend/       Next.js web app (agent chat + document library)
  backend/        FastAPI API (agent, uploads, processing, RAG)
docs/
  AGENT_ARCHITECTURE.md
  PROJECT_ROADMAP.md
  SUPABASE_SETUP.md
infra/
  init-db.sql     Database schema (run in Supabase SQL Editor)
sample-data/      Sample PDFs for local testing
uploads/          Local PDF storage (created on first upload)
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service and database health |
| `POST /agent/chat` | Unified agent chat with tool routing and session memory |
| `POST /agent/sessions` | Create a chat session |
| `GET /agent/sessions` | List saved chat sessions |
| `GET /agent/sessions/{id}` | Load a chat session and its messages |
| `DELETE /agent/sessions/{id}` | Delete a chat session and its messages |
| `POST /documents/upload` | Upload a PDF |
| `GET /documents` | List documents |
| `POST /documents/{id}/process` | Extract text, chunk, and embed |
| `POST /rag/query` | Legacy cited RAG answer endpoint |
| `POST /rag/search` | Legacy semantic search endpoint |

Full request/response schemas are available at http://localhost:8000/docs when the backend is running.

## Environment Variables

### Backend (`apps/backend/.env`)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase Postgres connection string (Session pooler) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (keep secret) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `CORS_ORIGINS` | Allowed frontend origins (e.g. `http://localhost:3000`) |
| `UPLOAD_DIR` | Local directory for uploaded PDFs (default: `uploads`) |
| `MAX_UPLOAD_MB` | Maximum upload size in MB |
| `EMBEDDING_*` | Embedding provider, model, and rate limits |
| `LLM_*` | Answer generation model and cache settings |
| `RAG_*` | Retrieval thresholds and source text limits |
| `AGENT_*` | Agent tool loop and response settings |
| `AVIATION_WEATHER_BASE_URL` | AviationWeather.gov API base URL |
| `OPERATIONAL_CACHE_TTL_SECONDS` | Optional cache TTL for operational API responses |

See [`apps/backend/.env.example`](apps/backend/.env.example) for all options and defaults.

### Frontend (`apps/frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |

## Operational Tools

The agent can call these live-data tools (all server-side):

| Tool | Provider | Purpose |
|------|----------|---------|
| `get_metar` | AviationWeather.gov | Current airport weather observations |
| `get_taf` | AviationWeather.gov | Terminal aerodrome forecasts |
| `get_international_sigmets` | AviationWeather.gov | International SIGMET hazard advisories |

AviationWeather.gov tools are public and require no API key.

## Running Tests

From `apps/backend` with the virtual environment activated:

```bash
pytest
```

From `apps/frontend`:

```bash
npm run lint
npm run build
```

Some tests require a configured database and API keys. See individual test modules for details.

## Roadmap

Implemented now:

- Agent chat endpoint
- `document_search` tool
- Operational tools: `get_metar`, `get_taf`, `get_international_sigmets`
- Tool activity and live operational source provenance in chat UI
- Conversation memory with persistent chat sessions

Planned next:

- MCP adapter layer
- Hybrid retrieval and reranking
- Observability dashboard
- Evaluation pipeline

See [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md) for details.
