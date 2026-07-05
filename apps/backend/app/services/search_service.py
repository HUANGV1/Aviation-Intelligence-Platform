"""Semantic search orchestration over embedded document chunks.

Purpose: Embeds user queries and retrieves top-k similar chunks from pgvector.
Interactions: Uses embedding_service.py and chunk_repository.py. Called by
api/rag.py for POST /rag/search.
"""

from uuid import UUID

from app.config import settings
from app.schemas.search import SearchResponse, SearchResultItem
from app.services.chunk_repository import search_similar_chunks
from app.services.embedding_service import EmbeddingError, embed_query


class SearchError(Exception):
    """Raised when semantic search cannot be completed."""


def _resolve_top_k(top_k: int | None, *, document_id: UUID | None) -> int:
    if top_k is not None:
        return min(top_k, settings.search_max_top_k)

    if document_id is not None:
        return min(5, settings.search_max_top_k)

    return min(settings.search_default_top_k, settings.search_max_top_k)


def search_document_chunks(
    query: str,
    *,
    document_id: UUID | None = None,
    top_k: int | None = None,
) -> SearchResponse:
    normalized_query = query.strip()
    if not normalized_query:
        raise SearchError("Query must not be empty.")

    limit = _resolve_top_k(top_k, document_id=document_id)

    try:
        query_embedding = embed_query(normalized_query)
    except EmbeddingError as exc:
        raise SearchError(str(exc)) from exc

    try:
        results = search_similar_chunks(
            query_embedding,
            limit=limit,
            document_id=document_id,
        )
    except RuntimeError as exc:
        raise SearchError("Semantic search failed.") from exc

    return SearchResponse(
        query=normalized_query,
        results=[
            SearchResultItem(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                document_name=row.document_name,
                chunk_index=row.chunk_index,
                text=row.text,
                page_number=row.page_number,
                section_title=row.section_title,
                similarity=row.similarity,
            )
            for row in results
        ],
        total=len(results),
    )
