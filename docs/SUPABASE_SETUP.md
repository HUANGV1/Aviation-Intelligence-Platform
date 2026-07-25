# Supabase Setup

This project uses **Supabase** as the MVP database. Supabase provides hosted PostgreSQL with the **pgvector** extension, so you do not need to install Postgres locally.

## What you get

- PostgreSQL database (free tier)
- pgvector for embedding search (Phase 4+)
- Optional Supabase Storage later for uploaded PDFs
- Web SQL editor for running migrations

## Step 1: Create a Supabase project

**You do NOT create a separate database.** When you create a Supabase project, Supabase automatically creates a Postgres database named `postgres` for you. Your job is only:

1. Create the project
2. Save the **database password** you choose during setup
3. Copy the connection string Supabase gives you

Steps:

1. Go to [https://supabase.com](https://supabase.com) and sign up (free).
2. Click **New project**.
3. Choose an organization (create one if needed).
4. Set:
   - **Project name:** `aviation-intelligence` (or any name)
   - **Database password:** generate a strong password and **save it somewhere** — this is NOT the service role key. You need this password for `DATABASE_URL`.
   - **Region:** pick the closest region to you
5. Click **Create new project** and wait ~2 minutes for provisioning.

When the dashboard loads, your database already exists. You are done with database creation.

## Step 2: Enable pgvector

1. In your Supabase project, open **SQL Editor** (left sidebar).
2. Click **New query**.
3. Paste and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

4. You should see **Success**. This is the same script in [`infra/init-db.sql`](../infra/init-db.sql).

To verify:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

You should get one row back.

## Step 3: Get your connection credentials

### Database URL (required — this is what you're missing)

This is **different** from the service role key you already copied.

| Credential | What it is | Used for |
|------------|------------|----------|
| `SUPABASE_URL` | Project URL | Supabase API (later) |
| `SUPABASE_SERVICE_ROLE_KEY` | API key from Settings → API | Supabase API (later) |
| `DATABASE_URL` | Postgres connection string | **Backend talking to the database** |

You already have the first two. You still need `DATABASE_URL`.

**Where to find it:**

1. Open your Supabase project dashboard.
2. Click the **gear icon** at the bottom left → **Project Settings**.
3. Click **Database** in the left menu (under Project Settings, NOT the main sidebar Database icon).
4. Scroll down to **Connection string**.
5. At the top of that section, set **Method** to **Session pooler** (recommended).
6. Click the **URI** tab.
7. Copy the string. It looks like:

```text
postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

8. Replace `[YOUR-PASSWORD]` with the **database password from Step 1** (when you created the project).

**Example** (fake password):

```text
postgresql://postgres.igkfbsyvskxenaposjxi:MyDbPassword123@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

If you forgot the database password: **Project Settings → Database → Reset database password**.

**Important for Windows:** Do **not** use the **Direct connection** host (`db.xxxx.supabase.co`). It often resolves to IPv6 only and fails with `getaddrinfo failed`. Always use **Session pooler**.

**Password special characters:** If your database password contains `#`, `@`, `/`, or `%`, URL-encode it in `DATABASE_URL` (for example, `#` becomes `%23`). Or reset your database password in Supabase to letters and numbers only.

**Do not** put the service role key in `DATABASE_URL`. That is a different credential.

### Supabase API keys (optional for Phase 1, useful later)

1. Go to **Project Settings** → **API**.
2. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** key → `SUPABASE_SERVICE_ROLE_KEY` (keep secret, backend only)

You will use these in later phases if you add Supabase Storage or Row Level Security.

## Step 4: Configure this repo

Copy env files if you have not already:

```bash
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/frontend/.env.local.example apps/frontend/.env.local
```

Edit **both** of these files with the same values:

- `.env` (repo root)
- `apps/backend/.env`

The backend reads from `apps/backend/.env` first. Keep them in sync.

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_DB_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

Edit `apps/frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Important:**
- Never commit real passwords or service role keys.
- The backend automatically adds `sslmode=require` for Supabase hosts.

### `.env` formatting rules (read this if health check says `DATABASE_URL is required`)

The backend loads `apps/backend/.env`. One bad line makes python-dotenv skip variables.

**Correct** — one line, no variable name inside the value:

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_ENCODED_PASSWORD@aws-1-us-west-2.pooler.supabase.com:5432/postgres
```

**Wrong** — do not do any of these:

```env
DATABASE_URL=DATABASE_URL="postgresql://..."
DATABASE_URL="postgresql://...   # missing closing quote
DATABASE_URL=postgresql://...:my#pass@...   # raw # starts a comment and breaks the line
```

Rules:
- Start the line with `DATABASE_URL=` once, then the URL only
- Do not wrap the line with extra quotes unless the whole URL is in matching `"..."`
- If the password contains `#`, use `%23` instead of `#`
- No spaces before or after `=`
- Do not paste `?sslmode=require` unless you want it (backend adds it automatically)

If uvicorn logs `python-dotenv could not parse statement starting at line X`, open `apps/backend/.env` and fix line X, then restart uvicorn.

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

## Step 6: Verify

1. Open http://localhost:8000/health

Expected response:

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

2. Open http://localhost:3000 — the frontend should show healthy backend and database status.

## Step 7: Apply chat memory tables (Phase 6)

If your Supabase project was created before conversation memory shipped, apply the new schema once:

1. Open Supabase Dashboard -> SQL Editor -> New query.
2. Paste the Phase 6 block from [`infra/init-db.sql`](../infra/init-db.sql) (`chat_sessions` and `chat_messages`), or rerun the full idempotent file.
3. Run it and confirm success.
4. Verify the tables exist:

```sql
select to_regclass('public.chat_sessions') as chat_sessions,
       to_regclass('public.chat_messages') as chat_messages;
```

Alternatively, from the backend environment:

```bash
cd apps/backend
python scripts/apply_init_db.py
```

No new env secrets are required for chat memory. The backend continues to use `DATABASE_URL`.

## Troubleshooting

### `password authentication failed`

- Double-check the password in `DATABASE_URL`.
- Reset the database password under **Project Settings → Database** if needed.

### `pgvector is not enabled`

- Run `CREATE EXTENSION IF NOT EXISTS vector;` in the Supabase SQL Editor again.

### `could not translate host name` / connection timeout

- Confirm you copied the full connection string from Supabase.
- Make sure your network allows outbound connections on port 5432.

### `DATABASE_URL is required`

- Open `apps/backend/.env` (not just the repo root `.env`)
- Check uvicorn terminal for `python-dotenv could not parse statement` — fix that line
- See the `.env` formatting rules in Step 4 above
- Restart uvicorn after saving

## What comes later

| Phase | Supabase usage |
|-------|----------------|
| Phase 2 | `documents` table via SQL migration in SQL Editor |
| Phase 3 | `document_chunks` table |
| Phase 4 | Vector columns + similarity search with pgvector (`vector(768)` + HNSW index on `document_chunks.embedding`) |
| Phase 6 | `chat_sessions` and `chat_messages` tables for persistent agent conversation memory |
| Post-MVP | Supabase Storage for PDF files instead of local disk |

## Free tier limits (good enough for MVP)

- 500 MB database
- Pauses after 1 week of inactivity (wake it from the dashboard)
- Sufficient for demo PDFs and development
