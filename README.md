# Aviation Intelligence Platform

Monorepo for the Aviation Intelligence AI Platform MVP — upload aviation PDFs, ask cited questions, and generate flight briefings.

## Phase 1 Status

This repository includes the Phase 1 foundation:

- Monorepo structure (`apps/frontend`, `apps/backend`)
- Next.js frontend (TypeScript)
- FastAPI backend (Python)
- Supabase (hosted PostgreSQL + pgvector)
- Backend health endpoint with database connectivity check
- Frontend page that displays backend health status

## Prerequisites

- Git
- Node.js 22+
- Python 3.12+
- Free [Supabase](https://supabase.com) account (no local Postgres install required)

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/HUANGV1/Aviation-Intelligence-Platform.git
cd Aviation-Intelligence-Platform
```

2. **Set up Supabase** — follow [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md) to create a project, enable pgvector, and copy your connection string.

3. Copy environment files:

```bash
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.local.example apps/frontend/.env.local
```

4. Paste your Supabase credentials into `apps/backend/.env`.

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
- Backend health: http://localhost:8000/health
- Backend docs: http://localhost:8000/docs

## Project Structure

```text
apps/
  frontend/     Next.js TypeScript app
  backend/      FastAPI Python app
docs/
  SUPABASE_SETUP.md
infra/
  init-db.sql   pgvector enable script (run in Supabase SQL Editor)
sample-data/    Demo PDFs (future phases)
.env.example
README.md
```

## Verification (Phase 1 Definition of Done)

With Supabase configured and backend + frontend running:

1. Frontend loads at http://localhost:3000
2. Frontend shows backend status as `healthy`
3. Frontend shows database status as `healthy`
4. `GET http://localhost:8000/health` returns JSON with `"status": "healthy"` and `"database": { "connected": true }`

Example health response:

```json
{
  "status": "healthy",
  "service": "aviation-intelligence-backend",
  "database": {
    "connected": true,
    "error": null
  }
}
```

## Environment Variables

| Variable | Location | Description |
|----------|----------|-------------|
| `DATABASE_URL` | `apps/backend/.env` | Supabase Postgres connection string |
| `SUPABASE_URL` | `apps/backend/.env` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `apps/backend/.env` | Supabase service role key (backend only, keep secret) |
| `CORS_ORIGINS` | `apps/backend/.env` | Allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | `apps/frontend/.env.local` | Backend URL for the frontend |

See [`.env.example`](.env.example) and [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md) for full setup steps.

## Next Steps

Phase 2 adds document upload, local file storage, and a document library UI. See `AVIATION_INTELLIGENCE_AI_PLATFORM.md` and `MVP_SCOPE_AND_TIMELINE.md` for the full MVP roadmap.
