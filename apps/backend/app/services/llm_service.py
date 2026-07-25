"""Gemini LLM service for structured JSON generation with prompt fingerprint caching.

Purpose: Provides a typed interface for grounded answer generation and future
briefing workflows. Interactions: Uses settings.gemini_api_key and is called by
rag_answer_service.py for cited RAG responses.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import BACKEND_DIR, settings
from app.tools.base import ToolDefinition

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


class LLMError(Exception):
    """Raised when LLM generation fails."""


class LLMQuotaError(LLMError):
    """Raised when Gemini quota or rate limits block generation."""


@dataclass(frozen=True)
class AgentFunctionCall:
    """One function-call request from a Gemini agent turn."""

    name: str
    args: dict


@dataclass(frozen=True)
class AgentTurnResult:
    """Result from a single Gemini agent turn."""

    text: str | None = None
    function_calls: tuple[AgentFunctionCall, ...] = ()

    @property
    def function_name(self) -> str | None:
        return self.function_calls[0].name if self.function_calls else None

    @property
    def function_args(self) -> dict | None:
        return dict(self.function_calls[0].args) if self.function_calls else None


@dataclass(frozen=True)
class LLMRequest:
    """Typed request for structured JSON generation."""

    system_instructions: str
    user_content: str
    schema_version: str = "v1"
    cache_namespace: str = "default"
    model: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None


@dataclass
class PromptCache:
    """File-backed TTL cache for LLM responses keyed by prompt fingerprint."""

    path: Path

    def __post_init__(self) -> None:
        self._data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Ignoring corrupt LLM cache at %s", self.path)
                self._data = {}

    def get(self, key: str) -> str | None:
        entry = self._data.get(key)
        if not entry:
            return None
        expires_at = entry.get("expires_at", 0)
        if time.time() > expires_at:
            return None
        return entry.get("value")

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._data[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        temp_path.replace(self.path)


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise LLMError(
                "GEMINI_API_KEY is required for answer generation. "
                "Set it in apps/backend/.env."
            )
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _resolve_cache_path() -> Path:
    path = Path(settings.llm_cache_path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path


def _build_fingerprint(request: LLMRequest) -> str:
    model = request.model or settings.llm_model
    temperature = (
        request.temperature
        if request.temperature is not None
        else settings.llm_temperature
    )
    max_tokens = (
        request.max_output_tokens
        if request.max_output_tokens is not None
        else settings.llm_max_output_tokens
    )
    payload = json.dumps(
        {
            "namespace": request.cache_namespace,
            "schema_version": request.schema_version,
            "model": model,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "system": request.system_instructions,
            "user": request.user_content,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_key(fingerprint: str) -> str:
    return f"llm:{fingerprint}"


def _extract_json_object(text: str) -> dict:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1:
        raise LLMError("LLM response did not contain a JSON object.")
    if end == -1:
        raise LLMError(
            "LLM response started JSON but was incomplete. Retry with fewer sources "
            "or a higher LLM_MAX_OUTPUT_TOKENS value."
        )
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError("LLM response contained invalid JSON.") from exc


def _json_generation_config(
    *,
    temperature: float,
    max_output_tokens: int,
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json",
    )


def _build_prompt(request: LLMRequest) -> str:
    return (
        f"{request.system_instructions.strip()}\n\n"
        f"{request.user_content.strip()}"
    )


def _is_quota_error(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.ClientError):
        status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if status_code == 429:
            return True
        message = str(exc).upper()
        return "RESOURCE_EXHAUSTED" in message or "QUOTA" in message
    return False


def _quota_error_message(model: str) -> str:
    return (
        f"Gemini quota or rate limit exceeded for model '{model}'. "
        "Wait and retry, check usage at https://ai.dev/rate-limit, "
        "or set LLM_MODEL in apps/backend/.env to a model your API key supports "
    )


def generate_json(
    request: LLMRequest,
    *,
    cache: PromptCache | None = None,
) -> dict:
    """Generate structured JSON from Gemini, with optional prompt fingerprint caching."""
    fingerprint = _build_fingerprint(request)
    key = _cache_key(fingerprint)

    if settings.llm_cache_enabled:
        cache = cache or PromptCache(_resolve_cache_path())
        cached = cache.get(key)
        if cached is not None:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.warning("Ignoring corrupt cached LLM entry for key %s", key)

    client = _get_client()
    model = request.model or settings.llm_model
    temperature = (
        request.temperature
        if request.temperature is not None
        else settings.llm_temperature
    )
    max_tokens = (
        request.max_output_tokens
        if request.max_output_tokens is not None
        else settings.llm_max_output_tokens
    )
    prompt = _build_prompt(request)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=_json_generation_config(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            text = getattr(response, "text", None)
            if text is None and response is not None:
                text = str(response)
            if not text:
                raise LLMError("LLM returned an empty response.")

            data = _extract_json_object(text)

            if settings.llm_cache_enabled:
                cache = cache or PromptCache(_resolve_cache_path())
                cache.set(key, json.dumps(data), settings.llm_cache_ttl_seconds)

            return data
        except LLMError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_quota_error(exc):
                logger.warning("Gemini quota/rate limit for model %s: %s", model, exc)
                raise LLMQuotaError(_quota_error_message(model)) from exc
            if attempt == 0:
                logger.warning("LLM request failed, retrying once: %s", exc)
                time.sleep(2)
            else:
                logger.warning("LLM request failed after retry: %s", exc)
                raise LLMError("Failed to generate LLM response.") from exc

    raise LLMError("Failed to generate LLM response.") from last_error


def _build_function_declarations(
    tool_definitions: list[ToolDefinition],
) -> list[types.FunctionDeclaration]:
    declarations: list[types.FunctionDeclaration] = []
    for tool in tool_definitions:
        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.parameters_schema,
            )
        )
    return declarations


def _extract_agent_turn(response: object) -> AgentTurnResult:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        text = getattr(response, "text", None)
        if text:
            return AgentTurnResult(text=str(text).strip())
        raise LLMError("LLM returned an empty agent response.")

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []

    text_parts: list[str] = []
    function_calls: list[AgentFunctionCall] = []
    for part in parts:
        function_call = getattr(part, "function_call", None)
        if function_call is not None:
            name = getattr(function_call, "name", None)
            args = getattr(function_call, "args", None) or {}
            if name:
                function_calls.append(
                    AgentFunctionCall(name=str(name), args=dict(args))
                )
            continue

        text = getattr(part, "text", None)
        if text:
            text_parts.append(str(text))

    if function_calls:
        return AgentTurnResult(function_calls=tuple(function_calls))

    if text_parts:
        return AgentTurnResult(text="\n".join(text_parts).strip())

    fallback_text = getattr(response, "text", None)
    if fallback_text:
        return AgentTurnResult(text=str(fallback_text).strip())

    raise LLMError("LLM returned an empty agent response.")


def generate_agent_turn(
    *,
    system_instructions: str,
    user_content: str,
    tool_definitions: list[ToolDefinition],
    model: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> AgentTurnResult:
    """Run one Gemini turn with optional function-calling tools."""
    client = _get_client()
    resolved_model = model or settings.llm_model
    resolved_temperature = (
        temperature if temperature is not None else settings.agent_temperature
    )
    resolved_max_tokens = (
        max_output_tokens
        if max_output_tokens is not None
        else settings.agent_max_output_tokens
    )

    declarations = _build_function_declarations(tool_definitions)
    tools = [types.Tool(function_declarations=declarations)] if declarations else None

    config = types.GenerateContentConfig(
        temperature=resolved_temperature,
        max_output_tokens=resolved_max_tokens,
        system_instruction=system_instructions,
        tools=tools,
    )

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=resolved_model,
                contents=user_content,
                config=config,
            )
            return _extract_agent_turn(response)
        except LLMError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_quota_error(exc):
                logger.warning(
                    "Gemini quota/rate limit for model %s: %s",
                    resolved_model,
                    exc,
                )
                raise LLMQuotaError(_quota_error_message(resolved_model)) from exc
            if attempt == 0:
                logger.warning("Agent turn failed, retrying once: %s", exc)
                time.sleep(2)
            else:
                logger.warning("Agent turn failed after retry: %s", exc)
                raise LLMError("Failed to generate agent response.") from exc

    raise LLMError("Failed to generate agent response.") from last_error
