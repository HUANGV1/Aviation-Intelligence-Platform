"""SQLAlchemy database engine and connectivity helpers.

Purpose: Provides a shared Postgres engine and verifies DB/pgvector availability.
Interactions: Uses DATABASE_URL from config.py. Used by document_repository.py,
scripts/apply_init_db.py, and the /health endpoint in main.py.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    return _engine


def check_database_connection() -> tuple[bool, str | None]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
            result = connection.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            vector_enabled = bool(result.scalar())
            if not vector_enabled:
                return (
                    False,
                    "pgvector is not enabled. Run infra/init-db.sql in the Supabase SQL Editor.",
                )
        return True, None
    except (SQLAlchemyError, ValueError) as exc:
        return False, str(exc)
