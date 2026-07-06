"""Database access layer for rag_queries audit/history records."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine


def insert_rag_query(
    *,
    query: str,
    answer: str,
    document_id: UUID | None,
    retrieved_chunk_ids: list[UUID],
) -> UUID | None:
    """Persist a RAG query record. Returns the new row id or None on failure."""
    insert_query = text(
        """
        INSERT INTO rag_queries (
            query,
            answer,
            document_id,
            retrieved_chunk_ids
        )
        VALUES (
            :query,
            :answer,
            :document_id,
            :retrieved_chunk_ids
        )
        RETURNING id
        """
    )

    chunk_id_strings = [str(chunk_id) for chunk_id in retrieved_chunk_ids]

    try:
        with get_engine().connect() as connection:
            row = connection.execute(
                insert_query,
                {
                    "query": query,
                    "answer": answer,
                    "document_id": document_id,
                    "retrieved_chunk_ids": chunk_id_strings,
                },
            ).one()
            connection.commit()
            return row.id
    except SQLAlchemyError:
        return None
