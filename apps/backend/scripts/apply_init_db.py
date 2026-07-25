"""Apply infra/init-db.sql to the configured database.

Purpose: Convenience script to run the database migration locally using DATABASE_URL.
Interactions: Reads infra/init-db.sql, executes statements via database.py engine,
and verifies the documents table exists. Alternative to pasting SQL into Supabase.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text

from app.database import get_engine


def split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_dollar_quote = False

    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        buffer.append(line)

        dollar_count = line.count("$$")
        if dollar_count % 2 == 1:
            in_dollar_quote = not in_dollar_quote

        if not in_dollar_quote and stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement.endswith(";"):
                statement = statement[:-1].strip()
            if statement:
                statements.append(statement)
            buffer = []

    trailing = "\n".join(buffer).strip()
    if trailing:
        statements.append(trailing.rstrip(";"))

    return statements


def main() -> None:
    sql_path = Path(__file__).resolve().parents[3] / "infra" / "init-db.sql"
    statements = split_sql_statements(sql_path.read_text(encoding="utf-8"))

    engine = get_engine()
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

        documents_exists = connection.execute(
            text("SELECT to_regclass('public.documents') IS NOT NULL")
        ).scalar()
        chunks_exists = connection.execute(
            text("SELECT to_regclass('public.document_chunks') IS NOT NULL")
        ).scalar()
        chat_sessions_exists = connection.execute(
            text("SELECT to_regclass('public.chat_sessions') IS NOT NULL")
        ).scalar()
        chat_messages_exists = connection.execute(
            text("SELECT to_regclass('public.chat_messages') IS NOT NULL")
        ).scalar()

    print(
        "migration ok",
        "documents table exists:",
        bool(documents_exists),
        "document_chunks table exists:",
        bool(chunks_exists),
        "chat_sessions table exists:",
        bool(chat_sessions_exists),
        "chat_messages table exists:",
        bool(chat_messages_exists),
    )


if __name__ == "__main__":
    main()
