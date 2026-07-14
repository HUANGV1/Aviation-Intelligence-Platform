"""Tests for the agent orchestrator and /agent/chat endpoint."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import RagCitation, RagQueryResponse
from app.services.agent_service import AgentError, run_agent_chat
from app.services.llm_service import AgentTurnResult, LLMQuotaError
from app.tools.base import ToolResult


@patch("app.services.agent_service.generate_agent_turn")
def test_run_agent_chat_returns_direct_answer(mock_turn) -> None:
    mock_turn.return_value = AgentTurnResult(
        text="I can help with aviation document questions and general aviation topics."
    )

    response = run_agent_chat("What can you do?")

    assert response.direct_answer is True
    assert response.answer.startswith("I can help")
    assert response.citations == []
    assert response.used_tools == []


@patch("app.services.agent_service._execute_tool")
@patch("app.services.agent_service.generate_agent_turn")
def test_run_agent_chat_invokes_document_search_tool(
    mock_turn,
    mock_execute_tool,
) -> None:
    chunk_id = uuid4()
    document_id = uuid4()
    mock_turn.return_value = AgentTurnResult(
        function_name="document_search",
        function_args={"query": "contributing factors"},
    )
    mock_execute_tool.return_value = ToolResult(
        tool_name="document_search",
        success=True,
        summary="Searched documents using 1 chunk and returned 1 cited source.",
        data={
            "query": "contributing factors",
            "answer": "Pilot fatigue was noted. [S1]",
            "citations": [
                {
                    "source_id": "S1",
                    "chunk_id": str(chunk_id),
                    "document_id": str(document_id),
                    "document_name": "accident-report.pdf",
                    "chunk_index": 0,
                    "text": "Pilot fatigue was a contributing factor.",
                    "page_number": 3,
                    "section_title": "Analysis",
                    "similarity": 0.82,
                }
            ],
            "insufficient_evidence": False,
            "used_chunk_count": 1,
        },
    )

    response = run_agent_chat("What were the contributing factors?")

    assert response.direct_answer is False
    assert response.used_tools == ["document_search"]
    assert len(response.tool_activities) == 1
    assert response.tool_activities[0].status == "success"
    assert len(response.citations) == 1
    assert response.citations[0].source_id == "S1"


@patch("app.services.agent_service._execute_tool")
@patch("app.services.agent_service.generate_agent_turn")
def test_run_agent_chat_returns_tool_failure(
    mock_turn,
    mock_execute_tool,
) -> None:
    mock_turn.return_value = AgentTurnResult(
        function_name="document_search",
        function_args={"query": "weather"},
    )
    mock_execute_tool.return_value = ToolResult(
        tool_name="document_search",
        success=False,
        summary="Document search failed.",
        error="Query must not be empty.",
    )

    response = run_agent_chat("What are the weather minimums?")

    assert response.insufficient_evidence is True
    assert response.used_tools == ["document_search"]
    assert response.tool_activities[0].status == "error"


def test_run_agent_chat_requires_non_empty_message() -> None:
    with pytest.raises(AgentError, match="Message must not be empty."):
        run_agent_chat("   ")


@patch("app.services.agent_service.generate_agent_turn")
def test_run_agent_chat_maps_quota_errors(mock_turn) -> None:
    mock_turn.side_effect = LLMQuotaError("Gemini quota exceeded.")

    with pytest.raises(LLMQuotaError):
        run_agent_chat("Hello")


@patch("app.services.agent_service.synthesize_operational_answer")
@patch("app.services.agent_service._execute_tool")
@patch("app.services.agent_service.generate_agent_turn")
def test_run_agent_chat_invokes_operational_tool(
    mock_turn,
    mock_execute_tool,
    mock_synthesize,
) -> None:
    from app.schemas.operational import OperationalRecord, OperationalSourceBundle
    from app.services.operational_normalization import bundle_to_dict, utc_now

    mock_turn.return_value = AgentTurnResult(
        function_name="get_metar",
        function_args={"ids": "KJFK"},
    )
    bundle = OperationalSourceBundle(
        provider="aviationweather.gov",
        source_type="METAR",
        source_url="https://aviationweather.gov/api/data/metar?ids=KJFK&format=json",
        retrieved_at=utc_now(),
        records=[
            OperationalRecord(
                record_id="metar-kjfk",
                title="METAR KJFK",
                summary="KJFK, flight category VFR",
                source_type="METAR",
                provider="aviationweather.gov",
                source_url="https://aviationweather.gov/api/data/metar?ids=KJFK&format=json",
                retrieved_at=utc_now(),
                location="KJFK",
            )
        ],
        pagination={"count": 1},
    )
    mock_execute_tool.return_value = ToolResult(
        tool_name="get_metar",
        success=True,
        summary="Retrieved 1 METAR.",
        data={"operational_source": bundle_to_dict(bundle)},
    )
    mock_synthesize.return_value = "Current KJFK METAR indicates VFR conditions."

    response = run_agent_chat("What is the current weather at KJFK?")

    assert response.used_tools == ["get_metar"]
    assert len(response.operational_sources) == 1
    assert response.operational_sources[0].source_type == "METAR"
    assert "KJFK" in response.answer


@patch("app.api.agent.run_agent_chat")
def test_agent_chat_endpoint_returns_response(mock_run) -> None:
    from app.schemas.agent import AgentChatResponse

    mock_run.return_value = AgentChatResponse(
        message="Hello",
        answer="Hello from the agent.",
        direct_answer=True,
    )

    with TestClient(app) as client:
        response = client.post("/agent/chat", json={"message": "Hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Hello from the agent."
    assert payload["direct_answer"] is True


@patch("app.api.agent.run_agent_chat")
def test_agent_chat_endpoint_maps_quota_errors(mock_run) -> None:
    mock_run.side_effect = LLMQuotaError("Gemini quota exceeded.")

    with TestClient(app) as client:
        response = client.post("/agent/chat", json={"message": "Hello"})

    assert response.status_code == 429
