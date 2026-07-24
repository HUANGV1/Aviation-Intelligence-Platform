"""Agent orchestration for unified chat with tool selection and execution.

Purpose: Routes user messages through a bounded Gemini tool-calling loop. The
document_search tool wraps the existing cited RAG pipeline without weakening
citation validation.
"""

from __future__ import annotations

from uuid import UUID

from app.config import settings
from app.schemas.agent import AgentChatResponse, ToolActivity
from app.schemas.rag import RagCitation
from app.services.operational_tools import (
    extract_operational_bundle,
    is_document_search_tool,
    is_operational_tool,
    synthesize_operational_answer,
)
from app.services.llm_service import LLMError, LLMQuotaError, generate_agent_turn
from app.tools.document_search import DOCUMENT_SEARCH_TOOL_NAME
from app.tools.base import ToolContext
from app.tools.registry import get_tool_registry
from app.tools.base import ToolResult


class AgentError(Exception):
    """Raised when the agent cannot complete a chat turn."""


AGENT_SYSTEM_INSTRUCTIONS = """You are Aviation Intelligence Platform, an aviation operations assistant.

You can answer general aviation questions directly when no live operational data or uploaded document evidence is required.

Tool routing:
- Use document_search for uploaded PDF evidence, accident reports, FAA guidance, and procedures.
- Use get_metar for current airport weather observations.
- Use get_taf for airport terminal forecasts.
- Use get_notams for active airport NOTAMs and published operational notices.
- Use get_international_sigmets for international area hazard advisories.

Rules:
- Prefer the correct live API tool when the user asks for current operational data.
- Prefer document_search when document evidence is needed and documents may be available.
- Answer directly for greetings, capability questions, or general aviation knowledge that does not
  require live data or uploaded document evidence.
- Do not invent document citations or claim document evidence without using document_search.
- Do not invent live operational data without using the corresponding API tool.
- Keep answers concise and professional.
- Do not provide operational flight advice beyond informational summaries.
"""


def _build_user_prompt(
    message: str,
    *,
    document_id: UUID | None,
    has_processed_documents_hint: bool,
) -> str:
    scope = (
        f"Scoped document_id: {document_id}"
        if document_id is not None
        else "Document scope: all processed documents"
    )
    availability = (
        "Processed documents are available for retrieval."
        if has_processed_documents_hint
        else "No processed documents are currently available."
    )
    return (
        f"User message: {message.strip()}\n"
        f"{scope}\n"
        f"{availability}"
    )


def _deserialize_citations(raw_citations: list[dict]) -> list[RagCitation]:
    citations: list[RagCitation] = []
    for item in raw_citations:
        try:
            citations.append(RagCitation.model_validate(item))
        except Exception:
            continue
    return citations


def _response_from_tool_result(
    message: str,
    tool_result: ToolResult,
    *,
    used_tools: list[str],
    tool_activities: list[ToolActivity],
) -> AgentChatResponse:
    data = tool_result.data
    citations = _deserialize_citations(data.get("citations", []))
    operational_sources = _deserialize_operational_sources(data)
    return AgentChatResponse(
        message=message,
        answer=str(data.get("answer", "")).strip() or tool_result.summary,
        citations=citations,
        operational_sources=operational_sources,
        insufficient_evidence=bool(data.get("insufficient_evidence", False)),
        used_tools=used_tools,
        tool_activities=tool_activities,
        direct_answer=False,
        used_chunk_count=int(data.get("used_chunk_count", 0)),
    )


def _deserialize_operational_sources(data: dict) -> list:
    from app.schemas.operational import OperationalSourceBundle

    raw = data.get("operational_source")
    if not raw:
        raw_sources = data.get("operational_sources", [])
        bundles = []
        for item in raw_sources:
            try:
                bundles.append(OperationalSourceBundle.model_validate(item))
            except Exception:
                continue
        return bundles
    try:
        return [OperationalSourceBundle.model_validate(raw)]
    except Exception:
        return []


def _response_from_operational_tool(
    message: str,
    tool_name: str,
    tool_result: ToolResult,
    *,
    used_tools: list[str],
    tool_activities: list[ToolActivity],
) -> AgentChatResponse:
    bundle = extract_operational_bundle(tool_result)
    operational_sources = [bundle] if bundle is not None else []
    answer = (
        synthesize_operational_answer(
            user_message=message,
            tool_name=tool_name,
            bundle=bundle,
        )
        if bundle is not None
        else tool_result.summary
    )
    return AgentChatResponse(
        message=message,
        answer=answer,
        citations=[],
        operational_sources=operational_sources,
        insufficient_evidence=not bool(bundle and bundle.records),
        used_tools=used_tools,
        tool_activities=tool_activities,
        direct_answer=False,
        used_chunk_count=0,
    )


def _execute_tool(
    tool_name: str,
    arguments: dict,
    *,
    context: ToolContext,
) -> ToolResult:
    registry = get_tool_registry()
    tool = registry.get(tool_name)
    if tool is None:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            summary=f"Unknown tool '{tool_name}'.",
            error=f"Tool '{tool_name}' is not registered.",
        )
    return tool.execute(arguments, context)


def run_agent_chat(
    message: str,
    *,
    document_id: UUID | None = None,
    top_k: int | None = None,
    has_processed_documents_hint: bool = True,
) -> AgentChatResponse:
    normalized_message = message.strip()
    if not normalized_message:
        raise AgentError("Message must not be empty.")

    registry = get_tool_registry()
    tool_definitions = registry.list_definitions()
    context = ToolContext(document_id=document_id)
    used_tools: list[str] = []
    tool_activities: list[ToolActivity] = []

    user_prompt = _build_user_prompt(
        normalized_message,
        document_id=document_id,
        has_processed_documents_hint=has_processed_documents_hint,
    )

    for _round in range(settings.agent_max_tool_rounds):
        try:
            turn = generate_agent_turn(
                system_instructions=AGENT_SYSTEM_INSTRUCTIONS,
                user_content=user_prompt,
                tool_definitions=tool_definitions,
            )
        except LLMQuotaError:
            raise
        except LLMError as exc:
            raise AgentError(str(exc)) from exc

        if turn.function_name:
            tool_name = turn.function_name
            arguments = dict(turn.function_args or {})

            if tool_name == DOCUMENT_SEARCH_TOOL_NAME and top_k is not None:
                arguments.setdefault("top_k", top_k)
            if is_document_search_tool(tool_name) and document_id is not None:
                arguments.setdefault("document_id", str(document_id))

            tool_result = _execute_tool(tool_name, arguments, context=context)
            used_tools.append(tool_name)
            tool_activities.append(
                ToolActivity(
                    tool_name=tool_name,
                    status="success" if tool_result.success else "error",
                    summary=tool_result.summary,
                    error=tool_result.error,
                )
            )

            if not tool_result.success:
                return AgentChatResponse(
                    message=normalized_message,
                    answer=(
                        tool_result.error
                        or "The requested tool failed before an answer could be produced."
                    ),
                    citations=[],
                    insufficient_evidence=True,
                    used_tools=used_tools,
                    tool_activities=tool_activities,
                    direct_answer=False,
                    used_chunk_count=0,
                )

            if is_document_search_tool(tool_name):
                return _response_from_tool_result(
                    normalized_message,
                    tool_result,
                    used_tools=used_tools,
                    tool_activities=tool_activities,
                )

            if is_operational_tool(tool_name):
                return _response_from_operational_tool(
                    normalized_message,
                    tool_name,
                    tool_result,
                    used_tools=used_tools,
                    tool_activities=tool_activities,
                )

            user_prompt = (
                f"{user_prompt}\n\n"
                f"Tool result from {tool_name}:\n"
                f"{tool_result.summary}\n"
                f"Data: {tool_result.data}"
            )
            continue

        if turn.text:
            return AgentChatResponse(
                message=normalized_message,
                answer=turn.text,
                citations=[],
                insufficient_evidence=False,
                used_tools=used_tools,
                tool_activities=tool_activities,
                direct_answer=True,
                used_chunk_count=0,
            )

    raise AgentError("Agent exceeded the maximum number of tool rounds.")
