"""Database access layer for document_chunks.

Purpose: Deletes, inserts, and lists text chunks for processed documents.
Interactions: Uses get_engine() from database.py and schemas/chunk.py models.
Called by the document processing flow in api/documents.py.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine
from app.schemas.chunk import ChunkResponse
from app.services.chunking import TextChunk


def _row_to_chunk(row) -> ChunkResponse:
    return ChunkResponse(
        id=row.id,
        document_id=row.document_id,
        chunk_index=row.chunk_index,
        text=row.text,
        page_number=row.page_number,
        section_title=row.section_title,
        token_count=row.token_count,
        created_at=row.created_at,
    )


def delete_chunks_for_document(document_id: UUID) -> None:
    query = text("DELETE FROM document_chunks WHERE document_id = :document_id")

    try:
        with get_engine().connect() as connection:
            connection.execute(query, {"document_id": document_id})
            connection.commit()
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to delete existing chunks.") from exc


def insert_chunks(document_id: UUID, chunks: list[TextChunk]) -> int:
    if not chunks:
        return 0

    insert_query = text(
        """
        INSERT INTO document_chunks (
            document_id,
            chunk_index,
            text,
            page_number,
            section_title,
            token_count
        )
        VALUES (
            :document_id,
            :chunk_index,
            :text,
            :page_number,
            :section_title,
            :token_count
        )
        """
    )

    try:
        with get_engine().connect() as connection:
            for chunk in chunks:
                connection.execute(
                    insert_query,
                    {
                        "document_id": document_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "page_number": chunk.page_number,
                        "section_title": chunk.section_title,
                        "token_count": chunk.token_count,
                    },
                )
            connection.commit()
        return len(chunks)
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to save document chunks.") from exc


def list_chunks_for_document(document_id: UUID) -> list[ChunkResponse]:
    query = text(
        """
        SELECT
            id,
            document_id,
            chunk_index,
            text,
            page_number,
            section_title,
            token_count,
            created_at
        FROM document_chunks
        WHERE document_id = :document_id
        ORDER BY chunk_index ASC
        """
    )

    try:
        with get_engine().connect() as connection:
            rows = connection.execute(query, {"document_id": document_id}).all()
            return [_row_to_chunk(row) for row in rows]
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to load document chunks.") from exc
