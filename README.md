# Aviation Intelligence Platform

Upload aviation PDFs, ask questions with cited answers, and explore your document library through a web console.

## Features

- **Document library** — upload PDFs, process them for search, and manage your collection
- **Cited Q&A** — ask questions scoped to one document or your full library; answers include source citations
- **Semantic search** — vector search over document chunks powered by pgvector
- **Health monitoring** — frontend and API report backend and database connectivity

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12+ |
| Database | Supabase (PostgreSQL + pgvector) |
| AI | Google Gemini (embeddings + answer generation) |

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

Upload a PDF from the document library, wait for processing to finish, then ask a question in the chat panel.

## Project Structure

```text
apps/
  frontend/       Next.js web app (document library + chat)
  backend/        FastAPI API (uploads, processing, RAG)
docs/
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
| `POST /documents/upload` | Upload a PDF |
| `GET /documents` | List documents |
| `POST /documents/{id}/process` | Extract text, chunk, and embed |
| `POST /rag/query` | Ask a question with cited answer |
| `POST /rag/search` | Semantic search over chunks |

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

See [`apps/backend/.env.example`](apps/backend/.env.example) for all options and defaults.

### Frontend (`apps/frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL (default: `http://localhost:8000`) |

## Running Tests

From `apps/backend` with the virtual environment activated:

```bash
pytest
```

Some tests require a configured database and API keys. See individual test modules for details.
