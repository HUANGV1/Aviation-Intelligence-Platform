"""Unit tests for the Gemini LLM service and prompt fingerprint cache."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services import llm_service
from app.services.llm_service import (
    AgentFunctionCall,
    AgentTurnResult,
    LLMError,
    LLMQuotaError,
    LLMRequest,
    PromptCache,
    _build_fingerprint,
    _extract_agent_turn,
    _extract_json_object,
    _json_generation_config,
    generate_json,
)


def test_build_fingerprint_is_stable() -> None:
    request = LLMRequest(
        system_instructions="System",
        user_content="User content",
        schema_version="rag-answer-v1",
        cache_namespace="rag-answer",
    )
    first = _build_fingerprint(request)
    second = _build_fingerprint(request)
    assert first == second


def test_build_fingerprint_changes_with_content() -> None:
    base = LLMRequest(
        system_instructions="System",
        user_content="User content",
        schema_version="rag-answer-v1",
    )
    changed = LLMRequest(
        system_instructions="System",
        user_content="Different content",
        schema_version="rag-answer-v1",
    )
    assert _build_fingerprint(base) != _build_fingerprint(changed)


def test_extract_json_object_from_fenced_response() -> None:
    payload = _extract_json_object(
        '```json\n{"answer": "test", "citations": ["S1"], "insufficient_evidence": false}\n```'
    )
    assert payload["answer"] == "test"
    assert payload["citations"] == ["S1"]


def test_extract_json_object_rejects_missing_json() -> None:
    with pytest.raises(LLMError, match="JSON object"):
        _extract_json_object("No structured payload here.")


def test_extract_json_object_reports_incomplete_json() -> None:
    with pytest.raises(LLMError, match="incomplete"):
        _extract_json_object('{"answer": "cut off before closing"')


def test_extract_agent_turn_preserves_multiple_function_calls() -> None:
    metar_call = MagicMock()
    metar_call.name = "get_metar"
    metar_call.args = {"ids": "KJFK"}

    notam_call = MagicMock()
    notam_call.name = "get_notams"
    notam_call.args = {"icao": "KJFK"}

    metar_part = MagicMock(function_call=metar_call, text=None)
    notam_part = MagicMock(function_call=notam_call, text=None)
    content = MagicMock(parts=[metar_part, notam_part])
    candidate = MagicMock(content=content)
    response = MagicMock(candidates=[candidate], text=None)

    turn = _extract_agent_turn(response)

    assert turn.text is None
    assert turn.function_calls == (
        AgentFunctionCall(name="get_metar", args={"ids": "KJFK"}),
        AgentFunctionCall(name="get_notams", args={"icao": "KJFK"}),
    )
    assert turn.function_name == "get_metar"
    assert turn.function_args == {"ids": "KJFK"}


def test_extract_agent_turn_returns_text_when_no_function_calls() -> None:
    text_part = MagicMock(function_call=None, text="Hello from the agent.")
    content = MagicMock(parts=[text_part])
    candidate = MagicMock(content=content)
    response = MagicMock(candidates=[candidate], text=None)

    turn = _extract_agent_turn(response)

    assert turn.function_calls == ()
    assert turn.text == "Hello from the agent."


def test_json_generation_config_requests_json_mime_type() -> None:
    config = _json_generation_config(temperature=0.2, max_output_tokens=500)

    assert config.temperature == 0.2
    assert config.max_output_tokens == 500
    assert config.response_mime_type == "application/json"


def test_prompt_cache_hit_and_miss(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    cache = PromptCache(cache_path)

    assert cache.get("llm:abc") is None

    cache.set("llm:abc", '{"answer":"cached"}', ttl_seconds=60)
    assert cache.get("llm:abc") == '{"answer":"cached"}'


def test_prompt_cache_expires_entries(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    cache = PromptCache(cache_path)
    cache._data["llm:expired"] = {
        "value": '{"answer":"old"}',
        "expires_at": time.time() - 1,
    }

    assert cache.get("llm:expired") is None


def test_prompt_cache_recovers_from_corrupt_file(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{not-json", encoding="utf-8")

    cache = PromptCache(cache_path)
    assert cache.get("llm:any") is None


@patch("app.services.llm_service._get_client")
def test_generate_json_uses_cache(mock_get_client: MagicMock, tmp_path: Path) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    request = LLMRequest(
        system_instructions="System",
        user_content="Question with sources",
        schema_version="test-v1",
        cache_namespace="test",
    )

    with (
        patch.object(llm_service.settings, "llm_cache_enabled", True),
        patch.object(llm_service.settings, "llm_cache_path", str(tmp_path / "cache.json")),
        patch.object(llm_service.settings, "llm_model", "test-model"),
        patch.object(llm_service.settings, "llm_temperature", 0.2),
        patch.object(llm_service.settings, "llm_max_output_tokens", 500),
    ):
        mock_response = MagicMock()
        mock_response.text = (
            '{"answer": "Grounded answer [S1]", "citations": ["S1"], '
            '"insufficient_evidence": false}'
        )
        mock_client.models.generate_content.return_value = mock_response

        first = generate_json(request)
        second = generate_json(request)

    assert first["answer"] == "Grounded answer [S1]"
    assert second["answer"] == "Grounded answer [S1]"
    mock_client.models.generate_content.assert_called_once()


@patch("app.services.llm_service._get_client")
def test_generate_json_retries_once(mock_get_client: MagicMock, tmp_path: Path) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = (
        '{"answer": "Retry success", "citations": ["S1"], "insufficient_evidence": false}'
    )
    mock_client.models.generate_content.side_effect = [
        RuntimeError("transient"),
        mock_response,
    ]

    request = LLMRequest(
        system_instructions="System",
        user_content="Retry test",
        schema_version="test-v1",
    )

    with (
        patch.object(llm_service.settings, "llm_cache_enabled", False),
        patch.object(llm_service.settings, "llm_cache_path", str(tmp_path / "cache.json")),
        patch("app.services.llm_service.time.sleep"),
    ):
        payload = generate_json(request)

    assert payload["answer"] == "Retry success"
    assert mock_client.models.generate_content.call_count == 2


@patch("app.services.llm_service._get_client")
def test_generate_json_raises_on_empty_response(mock_get_client: MagicMock) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = ""
    mock_client.models.generate_content.return_value = mock_response

    request = LLMRequest(
        system_instructions="System",
        user_content="Empty response test",
    )

    with (
        patch.object(llm_service.settings, "llm_cache_enabled", False),
        pytest.raises(LLMError, match="empty response"),
    ):
        generate_json(request)


@patch("app.services.llm_service._get_client")
def test_generate_json_raises_quota_error_without_retry(mock_get_client: MagicMock) -> None:
    from google.genai.errors import ClientError

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.models.generate_content.side_effect = ClientError(
        429,
        {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota exceeded"}},
        None,
    )

    request = LLMRequest(
        system_instructions="System",
        user_content="Quota test",
    )

    with (
        patch.object(llm_service.settings, "llm_cache_enabled", False),
        patch.object(llm_service.settings, "llm_model", "gemini-3.5-flash"),
        patch("app.services.llm_service.time.sleep") as mock_sleep,
        pytest.raises(LLMQuotaError, match="quota or rate limit"),
    ):
        generate_json(request)

    mock_client.models.generate_content.assert_called_once()
    mock_sleep.assert_not_called()
