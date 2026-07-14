"""Operational tool helpers shared by the agent orchestrator."""

from __future__ import annotations

import json
from typing import Any

from app.schemas.operational import OperationalRecord, OperationalSourceBundle
from app.services.llm_service import LLMError, LLMQuotaError, generate_json, LLMRequest
from app.tools.base import ToolResult
from app.tools.document_search import DOCUMENT_SEARCH_TOOL_NAME

OPERATIONAL_TOOL_NAMES = {
    "get_metar",
    "get_taf",
    "get_international_sigmets",
}

OPERATIONAL_SYNTHESIS_INSTRUCTIONS = """You are synthesizing a concise aviation operations answer from live tool data.

Rules:
- Use only the supplied operational source records.
- Mention source freshness using retrieved_at timestamps when relevant.
- If records are empty, say no matching live data was found instead of inventing conditions.
- Do not provide operational flight advice beyond informational summaries.
- Keep the answer concise and professional.
- Return ONLY valid JSON with no markdown fences.

Required JSON shape:
{
  "answer": "string"
}
"""


def is_document_search_tool(tool_name: str) -> bool:
    return tool_name == DOCUMENT_SEARCH_TOOL_NAME


def is_operational_tool(tool_name: str) -> bool:
    return tool_name in OPERATIONAL_TOOL_NAMES


def extract_operational_bundle(tool_result: ToolResult) -> OperationalSourceBundle | None:
    raw = tool_result.data.get("operational_source")
    if not raw:
        return None
    try:
        return OperationalSourceBundle.model_validate(raw)
    except Exception:
        return None


def serialize_operational_records(records: list[OperationalRecord], *, limit: int = 8) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for record in records[:limit]:
        serialized.append(
            {
                "record_id": record.record_id,
                "title": record.title,
                "summary": record.summary,
                "source_type": record.source_type,
                "provider": record.provider,
                "location": record.location,
                "retrieved_at": record.retrieved_at.isoformat(),
                "observed_at": record.observed_at.isoformat() if record.observed_at else None,
                "valid_from": record.valid_from.isoformat() if record.valid_from else None,
                "valid_to": record.valid_to.isoformat() if record.valid_to else None,
                "raw_text": record.raw_text,
                "metadata": record.metadata,
            }
        )
    return serialized


def build_operational_synthesis_prompt(
    *,
    user_message: str,
    tool_name: str,
    bundle: OperationalSourceBundle,
) -> str:
    payload = {
        "user_message": user_message,
        "tool_name": tool_name,
        "provider": bundle.provider,
        "source_type": bundle.source_type,
        "source_url": bundle.source_url,
        "retrieved_at": bundle.retrieved_at.isoformat(),
        "pagination": bundle.pagination,
        "records": serialize_operational_records(bundle.records),
    }
    return (
        f"Question: {user_message.strip()}\n\n"
        f"Operational source payload:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def synthesize_operational_answer(
    *,
    user_message: str,
    tool_name: str,
    bundle: OperationalSourceBundle,
) -> str:
    if not bundle.records:
        location = bundle.pagination.get("location") or bundle.pagination.get("ids")
        if location:
            return f"No live {bundle.source_type} records were found for {location} at request time."
        return f"No live {bundle.source_type} records matched the request."

    try:
        payload = generate_json(
            LLMRequest(
                system_instructions=OPERATIONAL_SYNTHESIS_INSTRUCTIONS,
                user_content=build_operational_synthesis_prompt(
                    user_message=user_message,
                    tool_name=tool_name,
                    bundle=bundle,
                ),
                schema_version="operational-answer-v1",
                cache_namespace="operational-answer",
            )
        )
    except (LLMQuotaError, LLMError):
        return _fallback_operational_answer(bundle)

    answer = str(payload.get("answer", "")).strip()
    if answer:
        return answer
    return _fallback_operational_answer(bundle)


def _fallback_operational_answer(bundle: OperationalSourceBundle) -> str:
    lines = [
        f"Live {bundle.source_type} data retrieved from {bundle.provider} at {bundle.retrieved_at.isoformat()}."
    ]
    for record in bundle.records[:5]:
        location = f" ({record.location})" if record.location else ""
        lines.append(f"- {record.title}{location}: {record.summary}")
    return "\n".join(lines)
