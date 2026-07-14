"""Tests for the document_search agent tool."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.schemas.rag import RagCitation, RagQueryResponse
from app.tools.base import ToolContext
from app.tools.document_search import DocumentSearchTool
from app.services.rag_answer_service import RagAnswerError


@patch("app.tools.document_search.answer_document_question")
def test_document_search_tool_returns_cited_result(mock_answer) -> None:
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

    tool = DocumentSearchTool()
    result = tool.execute(
        {"query": "What were the contributing factors?"},
        ToolContext(),
    )

    assert result.success is True
    assert result.tool_name == "document_search"
    assert result.data["answer"].startswith("Pilot fatigue")
    assert len(result.data["citations"]) == 1
    mock_answer.assert_called_once_with(
        "What were the contributing factors?",
        document_id=None,
        top_k=None,
        persist=False,
    )


@patch("app.tools.document_search.answer_document_question")
def test_document_search_tool_uses_context_document_scope(mock_answer) -> None:
    document_id = uuid4()
    mock_answer.return_value = RagQueryResponse(
        query="weather",
        answer="No evidence.",
        citations=[],
        insufficient_evidence=True,
        used_chunk_count=0,
    )

    tool = DocumentSearchTool()
    tool.execute(
        {"query": "What are the weather minimums?"},
        ToolContext(document_id=document_id),
    )

    mock_answer.assert_called_once_with(
        "What are the weather minimums?",
        document_id=document_id,
        top_k=None,
        persist=False,
    )


def test_document_search_tool_requires_query() -> None:
    tool = DocumentSearchTool()
    result = tool.execute({}, ToolContext())

    assert result.success is False
    assert result.error == "query is required."


@patch("app.tools.document_search.answer_document_question")
def test_document_search_tool_maps_rag_errors(mock_answer) -> None:
    mock_answer.side_effect = RagAnswerError("Search failed.")

    tool = DocumentSearchTool()
    result = tool.execute({"query": "weather minimums"}, ToolContext())

    assert result.success is False
    assert "Search failed." in (result.error or "")
