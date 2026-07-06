"""Tests for cited RAG answer orchestration and API endpoint."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import RagCitation, RagQueryResponse
from app.schemas.search import SearchResponse, SearchResultItem
from app.services import rag_answer_service
from app.services.llm_service import LLMQuotaError
from app.services.rag_answer_service import RagAnswerError, answer_document_question, build_rag_prompt

def test_answer_document_question_requires_non_empty_query() -> None:
    with pytest.raises(RagAnswerError, match="Query must not be empty."):
        answer_document_question("   ")


@patch("app.services.rag_answer_service.insert_rag_query")
@patch("app.services.rag_answer_service.search_document_chunks")
def test_answer_document_question_returns_insufficient_evidence_without_chunks(
    mock_search,
    mock_insert,
) -> None:
    mock_search.return_value = SearchResponse(query="weather", results=[], total=0)

    response = answer_document_question("What are the weather minimums?")

    assert response.insufficient_evidence is True
    assert response.citations == []
    assert response.used_chunk_count == 0
    mock_insert.assert_called_once()


@patch("app.services.rag_answer_service.insert_rag_query")
@patch("app.services.rag_answer_service.generate_json")
@patch("app.services.rag_answer_service.search_document_chunks")
def test_answer_document_question_returns_cited_answer(
    mock_search,
    mock_generate_json,
    mock_insert,
) -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    mock_search.return_value = SearchResponse(
        query="contributing factors",
        results=[
            SearchResultItem(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name="accident-report.pdf",
                chunk_index=0,
                text="Pilot fatigue was a contributing factor.",
                page_number=3,
                section_title="Analysis",
                similarity=0.82,
            )
        ],
        total=1,
    )
    mock_generate_json.return_value = {
        "answer": "Pilot fatigue was a contributing factor. [S1]",
        "citations": ["S1"],
        "insufficient_evidence": False,
    }

    response = answer_document_question(
        "What were the contributing factors?",
        document_id=document_id,
    )

    assert response.insufficient_evidence is False
    assert response.used_chunk_count == 1
    assert len(response.citations) == 1
    assert response.citations[0].source_id == "S1"
    assert response.citations[0].chunk_id == chunk_id
    mock_insert.assert_called_once()


@patch("app.services.rag_answer_service.insert_rag_query")
@patch("app.services.rag_answer_service.generate_json")
@patch("app.services.rag_answer_service.search_document_chunks")
def test_answer_document_question_downgrades_invalid_citations(
    mock_search,
    mock_generate_json,
    mock_insert,
) -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    mock_search.return_value = SearchResponse(
        query="weather",
        results=[
            SearchResultItem(
                chunk_id=chunk_id,
                document_id=document_id,
                document_name="advisory.pdf",
                chunk_index=0,
                text="Weather minimums apply below 500 feet.",
                page_number=2,
                section_title="Weather",
                similarity=0.88,
            )
        ],
        total=1,
    )
    mock_generate_json.return_value = {
        "answer": "Unsupported claim without valid citations.",
        "citations": ["S99"],
        "insufficient_evidence": False,
    }

    response = answer_document_question("What are the weather minimums?")

    assert response.insufficient_evidence is True
    assert response.citations == []
    assert response.used_chunk_count == 1
    mock_insert.assert_called_once()


def test_build_rag_prompt_includes_source_ids() -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    results = [
        SearchResultItem(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name="report.pdf",
            chunk_index=0,
            text="Sample excerpt.",
            page_number=1,
            section_title="Intro",
            similarity=0.9,
        )
    ]

    from app.services.rag_answer_service import _build_sources

    sources = _build_sources(results)
    prompt = build_rag_prompt("What happened?", sources)

    assert "Question: What happened?" in prompt
    assert "[S1]" in prompt
    assert str(chunk_id) in prompt
    assert "report.pdf" in prompt


def test_build_rag_prompt_truncates_long_source_text() -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    long_text = "A" * 2500
    results = [
        SearchResultItem(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name="report.pdf",
            chunk_index=0,
            text=long_text,
            page_number=1,
            section_title="Intro",
            similarity=0.9,
        )
    ]

    from app.services.rag_answer_service import _build_sources

    with patch.object(rag_answer_service.settings, "rag_max_source_text_chars", 1800):
        prompt = build_rag_prompt("What happened?", _build_sources(results))

    assert "..." in prompt
    assert long_text not in prompt
    assert prompt.count("A") == 1800


def test_build_rag_prompt_can_include_full_source_text() -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    long_text = "A" * 2500
    results = [
        SearchResultItem(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name="report.pdf",
            chunk_index=0,
            text=long_text,
            page_number=1,
            section_title="Intro",
            similarity=0.9,
        )
    ]

    from app.services.rag_answer_service import _build_sources

    with patch.object(rag_answer_service.settings, "rag_max_source_text_chars", 0):
        prompt = build_rag_prompt("What happened?", _build_sources(results))

    assert "..." not in prompt
    assert long_text in prompt
    assert prompt.count("A") == 2500


@patch("app.api.rag.answer_document_question")
def test_query_endpoint_returns_cited_answer(mock_answer) -> None:
    chunk_id = uuid4()
    document_id = uuid4()

    mock_answer.return_value = RagQueryResponse(
        query="contributing factors",
        answer="Pilot fatigue was noted. [S1]",
        citations=[
            RagCitation(
                source_id="S1",
                chunk_id=chunk_id,
                document_id=document_id,
                document_name="accident-report.pdf",
                chunk_index=0,
                text="Pilot fatigue was a contributing factor.",
                page_number=3,
                section_title="Analysis",
                similarity=0.82,
            )
        ],
        insufficient_evidence=False,
        used_chunk_count=1,
    )

    with TestClient(app) as client:
        response = client.post(
            "/rag/query",
            json={"query": "contributing factors"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].startswith("Pilot fatigue")
    assert payload["insufficient_evidence"] is False
    assert payload["citations"][0]["source_id"] == "S1"


@patch("app.api.rag.answer_document_question")
def test_query_endpoint_maps_quota_errors(mock_answer) -> None:
    mock_answer.side_effect = LLMQuotaError(
        "Gemini quota or rate limit exceeded for model 'gemini-3.5-flash'."
    )

    with TestClient(app) as client:
        response = client.post(
            "/rag/query",
            json={"query": "contributing factors"},
        )

    assert response.status_code == 429
    assert "quota" in response.json()["detail"].lower()


@patch("app.api.rag.answer_document_question")
def test_query_endpoint_maps_validation_errors(mock_answer) -> None:
    mock_answer.side_effect = RagAnswerError("Query must not be empty.")

    with TestClient(app) as client:
        response = client.post(
            "/rag/query",
            json={"query": "   "},
        )

    assert response.status_code == 422 or response.status_code == 400
