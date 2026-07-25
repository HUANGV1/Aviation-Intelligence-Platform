# Supabase Setup

This project uses **Supabase** for hosted PostgreSQL with the **pgvector** extension. You do not need to install Postgres locally.

## What you get

- PostgreSQL database (free tier is enough for local demos)
- pgvector for embedding search (`vector(768)` + HNSW index)
- Web SQL Editor for applying [`infra/init-db.sql`](../infra/init-db.sql)
- Optional later: Supabase Storage for PDFs (today files stay on local disk under `uploads/`)

## Schema overview

`infra/init-db.sql` creates (idempotently):

| Table | Purpose |
|-------|---------|
| `documents` | Uploaded PDF metadata |
| `document_chunks` | Chunk text + embeddings |
| `rag_queries` | Optional audit rows for `/rag/query` |
| `chat_sessions` | Agent conversation sessions |
| `chat_messages` | Persisted chat turns (citations, ops sources, tool activity) |

---

## Step 1: Create a Supabase project

Creating a Supabase project also creates a Postgres database named `postgres`. You only need to:

1. Create the project
2. Save the **database password** from setup
3. Later copy the **Session pooler** connection string

Steps:

1. Go to [https://supabase.com](https://supabase.com) and sign in.
2. Click **New project**.
3. Choose an organization.
4. Set:
   - **Project name:** e.g. `aviation-intelligence`
   - **Database password:** generate a strong password and **save it** — this is for `DATABASE_URL`, not the service role key
   - **Region:** closest to you
5. Click **Create new project** and wait for provisioning.

---

## Step 2: Enable pgvector and apply the schema

1. Open **SQL Editor** → **New query**.
2. Paste the full contents of [`infra/init-db.sql`](../infra/init-db.sql) and run it.

The script starts with `CREATE EXTENSION IF NOT EXISTS vector;` and creates all application tables/indexes.

To verify:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';

SELECT to_regclass('public.documents') AS documents,
       to_regclass('public.document_chunks') AS document_chunks,
       to_regclass('public.chat_sessions') AS chat_sessions,
       to_regclass('public.chat_messages') AS chat_messages;
```

You should see the vector extension row and non-null table OIDs.

Alternatively, from a configured backend environment:

```bash
cd apps/backend
python scripts/apply_init_db.py
```

---

## Step 3: Connection credentials

| Variable | What it is | Required? |
|----------|------------|-----------|
| `DATABASE_URL` | Postgres connection string (Session pooler URI) | **Yes** — backend SQLAlchemy |
| `SUPABASE_URL` | Project URL (`https://….supabase.co`) | Optional today |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role API key (Settings → API) | Optional today; **never** put in frontend |

### Database URL (required)

1. Supabase dashboard → **Project Settings** (gear) → **Database**.
2. Under **Connection string**, set **Method** to **Session pooler**.
3. Open the **URI** tab and copy the string. Example shape:

```text
postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

4. Replace `[YOUR-PASSWORD]` with the database password from Step 1.

**Windows tip:** Prefer **Session pooler**. The Direct host (`db.xxxx.supabase.co`) often fails with IPv6/`getaddrinfo` errors.

**Password special characters:** URL-encode `#`, `@`, `/`, `%` in the password (e.g. `#` → `%23`), or reset the password to alphanumeric only.

**Do not** put the service role key in `DATABASE_URL`.

### Optional API keys

**Project Settings → API**:

- **Project URL** → `SUPABASE_URL`
- **service_role** → `SUPABASE_SERVICE_ROLE_KEY` (secret, backend only)

Useful later for Storage or RLS. The app talks to Postgres via `DATABASE_URL` today.

---

## Step 4: Configure this repo

```bash
# macOS / Linux / Git Bash
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.local.example apps/frontend/.env.local
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
Copy-Item apps/backend/.env.example apps/backend/.env
Copy-Item apps/frontend/.env.local.example apps/frontend/.env.local
```

Edit `apps/backend/.env` (the backend loads this file; root `.env` is optional shared defaults):

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_ENCODED_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=
GEMINI_API_KEY=your-gemini-key
CORS_ORIGINS=http://localhost:3000
```

Edit `apps/frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Notes:

- Never commit real passwords or keys
- The backend adds `sslmode=require` automatically for Supabase hosts

### `.env` formatting (if health says `DATABASE_URL is required`)

One bad line can make dotenv skip variables.

**Correct:**

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_ENCODED_PASSWORD@aws-1-us-west-2.pooler.supabase.com:5432/postgres
```

**Wrong:**

```env
DATABASE_URL=DATABASE_URL="postgresql://..."
DATABASE_URL="postgresql://...   # missing closing quote
DATABASE_URL=postgresql://...:my#pass@...   # raw # starts a comment
```

Rules:

- One `DATABASE_URL=` then the URL only
- Encode `#` in passwords as `%23`
- No spaces around `=`
- Restart uvicorn after saving

If uvicorn logs `python-dotenv could not parse statement starting at line X`, fix that line in `apps/backend/.env`.

---

## Step 5: Start the app

**Terminal 1 — backend:**

```bash
cd apps/backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```bash
cd apps/frontend
npm install
npm run dev
```

---

## Step 6: Verify

1. Open http://localhost:8000/health

Expected:

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

2. Open http://localhost:3000 — the UI should report healthy backend and database status.

3. Upload a PDF, process it, and send a chat message to confirm end-to-end DB writes.

---

## Troubleshooting

### `password authentication failed`

- Check the password embedded in `DATABASE_URL`
- Reset under **Project Settings → Database** if needed

### `pgvector is not enabled`

- Re-run `CREATE EXTENSION IF NOT EXISTS vector;` or the full `infra/init-db.sql`

### `could not translate host name` / connection timeout

- Confirm Session pooler URI (not Direct) on Windows
- Confirm outbound access to the pooler host/port

### `DATABASE_URL is required`

- Edit `apps/backend/.env` (not only the repo-root `.env`)
- Fix any dotenv parse errors, then restart uvicorn

### Chat sessions fail but documents work

- Confirm `chat_sessions` / `chat_messages` exist (Step 2 verify query)
- Re-run `infra/init-db.sql` or `python scripts/apply_init_db.py`

---

## Free tier notes

- ~500 MB database
- Projects may pause after inactivity (wake from the dashboard)
- Enough for demo PDFs and local development

## Later options

- Supabase Storage instead of local `uploads/`
- Row Level Security once end-user auth exists
- Never expose `SUPABASE_SERVICE_ROLE_KEY` to the Next.js client
