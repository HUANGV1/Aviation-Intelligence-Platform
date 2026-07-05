"""Tests for semantic search API and retrieval orchestration."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.search import SearchResponse, SearchResultItem
from app.services.chunk_repository import SimilarChunkRow
from app.services.search_service import SearchError, search_document_chunks


def test_search_document_chunks_requires_non_empty_query() -> None:
    with pytest.raises(SearchError, match="Query must not be empty."):
        search_document_chunks("   ")


@patch("app.services.search_service.search_similar_chunks")
@patch("app.services.search_service.embed_query")
def test_search_document_chunks_returns_ranked_results(
    mock_embed_query,
    mock_search_similar_chunks,
) -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    mock_embed_query.return_value = [0.1] * 768
    mock_search_similar_chunks.return_value = [
        SimilarChunkRow(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name="test-process.pdf",
            chunk_index=0,
            text="Sample chunk text.",
            page_number=1,
            section_title="Introduction",
            similarity=0.91,
        )
    ]

    response = search_document_chunks(
        "What guidance is provided?",
        document_id=document_id,
        top_k=5,
    )

    assert response.query == "What guidance is provided?"
    assert response.total == 1
    assert response.results[0].chunk_id == chunk_id
    assert response.results[0].document_name == "test-process.pdf"
    assert response.results[0].page_number == 1
    mock_embed_query.assert_called_once_with("What guidance is provided?")
    mock_search_similar_chunks.assert_called_once()


@patch("app.api.rag.search_document_chunks")
def test_search_endpoint_returns_results(mock_search_document_chunks) -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    mock_search_document_chunks.return_value = SearchResponse(
        query="weather minimums",
        results=[
            SearchResultItem(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name="test-process.pdf",
                chunk_index=0,
                text="Weather minimums apply below 500 feet.",
                page_number=2,
                section_title="Weather",
                similarity=0.88,
            )
        ],
        total=1,
    )

    with TestClient(app) as client:
        response = client.post(
            "/rag/search",
            json={"query": "weather minimums"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "weather minimums"
    assert payload["total"] == 1
    assert payload["results"][0]["document_name"] == "test-process.pdf"
