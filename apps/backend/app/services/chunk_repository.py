"""Database access layer for document_chunks.

Purpose: Deletes, inserts, lists, and searches text chunks for processed documents.
Interactions: Uses get_engine() from database.py and schemas/chunk.py models.
Called by document processing and semantic search services.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine
from app.schemas.chunk import ChunkResponse
from app.services.chunking import TextChunk


@dataclass(frozen=True)
class SimilarChunkRow:
    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    text: str
    page_number: int | None
    section_title: str | None
    similarity: float


def _embedding_to_pgvector(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


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


def insert_chunks(
    document_id: UUID,
    chunks: list[TextChunk],
    *,
    embeddings: list[list[float]] | None = None,
) -> int:
    if not chunks:
        return 0

    if embeddings is not None and len(embeddings) != len(chunks):
        raise ValueError("Embeddings must match the number of chunks.")

    insert_query = text(
        """
        INSERT INTO document_chunks (
            document_id,
            chunk_index,
            text,
            page_number,
            section_title,
            token_count,
            embedding
        )
        VALUES (
            :document_id,
            :chunk_index,
            :text,
            :page_number,
            :section_title,
            :token_count,
            CAST(:embedding AS vector)
        )
        """
    )

    try:
        with get_engine().connect() as connection:
            for index, chunk in enumerate(chunks):
                embedding_value = None
                if embeddings is not None:
                    embedding_value = _embedding_to_pgvector(embeddings[index])

                connection.execute(
                    insert_query,
                    {
                        "document_id": document_id,
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "page_number": chunk.page_number,
                        "section_title": chunk.section_title,
                        "token_count": chunk.token_count,
                        "embedding": embedding_value,
                    },
                )
            connection.commit()
        return len(chunks)
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to save document chunks.") from exc


def update_chunk_embeddings(
    document_id: UUID,
    *,
    chunk_indexes: list[int],
    embeddings: list[list[float]],
) -> int:
    if not chunk_indexes:
        return 0

    if len(chunk_indexes) != len(embeddings):
        raise ValueError("Chunk indexes must match the number of embeddings.")

    update_query = text(
        """
        UPDATE document_chunks
        SET embedding = CAST(:embedding AS vector)
        WHERE document_id = :document_id
          AND chunk_index = :chunk_index
        """
    )

    updated_count = 0

    try:
        with get_engine().connect() as connection:
            for chunk_index, embedding in zip(chunk_indexes, embeddings):
                result = connection.execute(
                    update_query,
                    {
                        "document_id": document_id,
                        "chunk_index": chunk_index,
                        "embedding": _embedding_to_pgvector(embedding),
                    },
                )
                updated_count += result.rowcount
            connection.commit()
        return updated_count
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to save chunk embeddings.") from exc


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


def search_similar_chunks(
    query_embedding: list[float],
    *,
    limit: int,
    document_id: UUID | None = None,
) -> list[SimilarChunkRow]:
    if limit <= 0:
        return []

    params: dict[str, object] = {
        "query_embedding": _embedding_to_pgvector(query_embedding),
        "limit": limit,
    }

    document_filter = ""
    if document_id is not None:
        document_filter = "AND dc.document_id = :document_id"
        params["document_id"] = document_id

    query = text(
        f"""
        SELECT
            dc.id AS chunk_id,
            dc.document_id,
            d.original_filename AS document_name,
            dc.chunk_index,
            dc.text,
            dc.page_number,
            dc.section_title,
            1 - (dc.embedding <=> CAST(:query_embedding AS vector)) AS similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.embedding IS NOT NULL
        {document_filter}
        ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :limit
        """
    )

    try:
        with get_engine().connect() as connection:
            rows = connection.execute(query, params).all()
            return [
                SimilarChunkRow(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    document_name=row.document_name,
                    chunk_index=row.chunk_index,
                    text=row.text,
                    page_number=row.page_number,
                    section_title=row.section_title,
                    similarity=float(row.similarity),
                )
                for row in rows
            ]
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to search document chunks.") from exc
