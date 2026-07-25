"""Agent orchestration for unified chat with tool selection and execution.

Purpose: Routes user messages through a bounded Gemini tool-calling loop. The
document_search tool wraps the existing cited RAG pipeline without weakening
citation validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import UUID

from app.config import settings
from app.schemas.agent import AgentChatResponse, ToolActivity
from app.schemas.chat import ChatMessageRecord
from app.schemas.operational import OperationalSourceBundle
from app.schemas.rag import RagCitation
from app.services.chat_message_repository import (
    ChatMessageError,
    get_recent_messages_for_memory,
    insert_message,
)
from app.services.chat_session_repository import (
    ChatSessionError,
    create_session,
    session_exists,
    update_session_title,
)
from app.services.llm_service import AgentFunctionCall, LLMError, LLMQuotaError, generate_agent_turn
from app.services.operational_tools import (
    extract_operational_bundle,
    is_document_search_tool,
    is_operational_tool,
    synthesize_operational_answer,
)
from app.tools.base import ToolContext, ToolResult
from app.tools.document_search import DOCUMENT_SEARCH_TOOL_NAME
from app.tools.registry import get_tool_registry


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
- Request one or more tools in a single turn when the user's query needs multiple data sources.
- Example: for "METAR and NOTAMs for KJFK", call both get_metar and get_notams together.

Rules:
- Prefer the correct live API tool when the user asks for current operational data.
- Prefer document_search when document evidence is needed and documents may be available.
- Answer directly for greetings, capability questions, or general aviation knowledge that does not
  require live data or uploaded document evidence.
- After tool results are provided, synthesize one concise answer covering all retrieved data.
- Do not invent document citations or claim document evidence without using document_search.
- Do not invent live operational data without using the corresponding API tool.
- Keep answers concise and professional.
- Do not provide operational flight advice beyond informational summaries.
"""


@dataclass
class _AccumulatedToolResults:
    citations: list[RagCitation] = field(default_factory=list)
    operational_sources: list[OperationalSourceBundle] = field(default_factory=list)
    used_chunk_count: int = 0
    insufficient_evidence: bool = False
    document_answer: str | None = None
    operational_tool_names: list[str] = field(default_factory=list)


def _derive_session_title(message: str, *, max_length: int = 60) -> str:
    collapsed = " ".join(message.strip().split())
    if len(collapsed) <= max_length:
        return collapsed
    return collapsed[: max_length - 1].rstrip() + "…"


def _format_conversation_history(messages: list[ChatMessageRecord]) -> str:
    if not messages:
        return ""

    lines: list[str] = ["Recent conversation:"]
    for item in messages:
        role_label = "User" if item.role == "user" else "Assistant"
        lines.append(f"{role_label}: {item.content.strip()}")
    return "\n".join(lines)


def _build_user_prompt(
    message: str,
    *,
    document_id: UUID | None,
    has_processed_documents_hint: bool,
    conversation_history: list[ChatMessageRecord] | None = None,
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
    history_block = _format_conversation_history(conversation_history or [])
    sections = [
        history_block,
        f"User message: {message.strip()}",
        scope,
        availability,
    ]
    return "\n".join(section for section in sections if section.strip())


def _resolve_session_id(
    session_id: UUID | None,
    *,
    document_id: UUID | None,
    persist_memory: bool,
) -> UUID | None:
    if not persist_memory:
        return session_id

    if session_id is not None:
        if not session_exists(session_id):
            raise AgentError("Chat session not found.")
        return session_id

    session = create_session(document_id=document_id)
    return session.id


def _load_conversation_history(session_id: UUID | None) -> list[ChatMessageRecord]:
    if session_id is None:
        return []

    return get_recent_messages_for_memory(
        session_id,
        max_turns=settings.agent_memory_max_turns,
    )


def _persist_chat_turn(
    session_id: UUID | None,
    *,
    user_message: str,
    response: AgentChatResponse,
    set_title: bool,
) -> None:
    if session_id is None:
        return

    insert_message(
        session_id=session_id,
        role="user",
        content=user_message,
    )
    insert_message(
        session_id=session_id,
        role="assistant",
        content=response.answer,
        citations=response.citations,
        operational_sources=response.operational_sources,
        tool_activities=response.tool_activities,
        used_tools=response.used_tools,
        direct_answer=response.direct_answer,
        insufficient_evidence=response.insufficient_evidence,
        used_chunk_count=response.used_chunk_count,
    )

    if set_title:
        update_session_title(session_id, _derive_session_title(user_message))


def _attach_session_id(
    response: AgentChatResponse,
    session_id: UUID | None,
) -> AgentChatResponse:
    return response.model_copy(update={"session_id": session_id})


def _finalize_agent_response(
    response: AgentChatResponse,
    *,
    session_id: UUID | None,
    user_message: str,
    persist_memory: bool,
    is_new_session: bool,
) -> AgentChatResponse:
    if persist_memory and session_id is not None:
        try:
            _persist_chat_turn(
                session_id,
                user_message=user_message,
                response=response,
                set_title=is_new_session,
            )
        except (ChatSessionError, ChatMessageError) as exc:
            raise AgentError("Failed to persist conversation memory.") from exc

    return _attach_session_id(response, session_id)


def _deserialize_citations(raw_citations: list[dict]) -> list[RagCitation]:
    citations: list[RagCitation] = []
    for item in raw_citations:
        try:
            citations.append(RagCitation.model_validate(item))
        except Exception:
            continue
    return citations


def _deserialize_operational_sources(data: dict) -> list[OperationalSourceBundle]:
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


def _accumulate_tool_result(
    accumulated: _AccumulatedToolResults,
    tool_name: str,
    tool_result: ToolResult,
) -> None:
    if is_document_search_tool(tool_name):
        data = tool_result.data
        accumulated.citations.extend(_deserialize_citations(data.get("citations", [])))
        accumulated.used_chunk_count = max(
            accumulated.used_chunk_count,
            int(data.get("used_chunk_count", 0)),
        )
        if bool(data.get("insufficient_evidence", False)):
            accumulated.insufficient_evidence = True
        answer = str(data.get("answer", "")).strip()
        if answer:
            accumulated.document_answer = answer
        return

    if is_operational_tool(tool_name):
        bundle = extract_operational_bundle(tool_result)
        if bundle is not None:
            accumulated.operational_sources.append(bundle)
            accumulated.operational_tool_names.append(tool_name)
            if not bundle.records:
                accumulated.insufficient_evidence = True


def _format_tool_result_for_prompt(tool_name: str, tool_result: ToolResult) -> str:
    return (
        f"Tool result from {tool_name}:\n"
        f"Success: {tool_result.success}\n"
        f"Summary: {tool_result.summary}\n"
        f"Data: {json.dumps(tool_result.data, ensure_ascii=False, default=str)}"
    )


def _build_tool_failure_response(
    message: str,
    tool_result: ToolResult,
    *,
    used_tools: list[str],
    tool_activities: list[ToolActivity],
) -> AgentChatResponse:
    return AgentChatResponse(
        message=message,
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


def _resolve_insufficient_evidence(accumulated: _AccumulatedToolResults) -> bool:
    if accumulated.citations or any(
        bundle.records for bundle in accumulated.operational_sources
    ):
        return False
    return accumulated.insufficient_evidence


def _build_final_tool_response(
    message: str,
    answer: str,
    accumulated: _AccumulatedToolResults,
    *,
    used_tools: list[str],
    tool_activities: list[ToolActivity],
) -> AgentChatResponse:
    return AgentChatResponse(
        message=message,
        answer=answer.strip(),
        citations=accumulated.citations,
        operational_sources=accumulated.operational_sources,
        insufficient_evidence=_resolve_insufficient_evidence(accumulated),
        used_tools=used_tools,
        tool_activities=tool_activities,
        direct_answer=False,
        used_chunk_count=accumulated.used_chunk_count,
    )


def _build_fallback_tool_response(
    message: str,
    accumulated: _AccumulatedToolResults,
    *,
    used_tools: list[str],
    tool_activities: list[ToolActivity],
) -> AgentChatResponse:
    answer_parts: list[str] = []
    if accumulated.document_answer:
        answer_parts.append(accumulated.document_answer)

    for tool_name, bundle in zip(
        accumulated.operational_tool_names,
        accumulated.operational_sources,
        strict=False,
    ):
        answer_parts.append(
            synthesize_operational_answer(
                user_message=message,
                tool_name=tool_name,
                bundle=bundle,
            )
        )

    answer = "\n\n".join(part for part in answer_parts if part.strip()).strip()
    if not answer:
        answer = "Tool data was retrieved, but no final answer could be synthesized."

    return _build_final_tool_response(
        message,
        answer,
        accumulated,
        used_tools=used_tools,
        tool_activities=tool_activities,
    )


def _prepare_tool_arguments(
    call: AgentFunctionCall,
    *,
    document_id: UUID | None,
    top_k: int | None,
) -> tuple[str, dict]:
    tool_name = call.name
    arguments = dict(call.args)

    if tool_name == DOCUMENT_SEARCH_TOOL_NAME and top_k is not None:
        arguments.setdefault("top_k", top_k)
    if is_document_search_tool(tool_name) and document_id is not None:
        # UI/request scope always wins over any model-supplied document_id.
        arguments["document_id"] = str(document_id)

    return tool_name, arguments


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
    session_id: UUID | None = None,
    document_id: UUID | None = None,
    top_k: int | None = None,
    has_processed_documents_hint: bool = True,
    persist_memory: bool = True,
) -> AgentChatResponse:
    normalized_message = message.strip()
    if not normalized_message:
        raise AgentError("Message must not be empty.")

    is_new_session = persist_memory and session_id is None
    resolved_session_id = _resolve_session_id(
        session_id,
        document_id=document_id,
        persist_memory=persist_memory,
    )
    conversation_history = (
        _load_conversation_history(resolved_session_id)
        if persist_memory
        else []
    )

    registry = get_tool_registry()
    tool_definitions = registry.list_definitions()
    context = ToolContext(document_id=document_id)
    used_tools: list[str] = []
    tool_activities: list[ToolActivity] = []
    accumulated = _AccumulatedToolResults()

    user_prompt = _build_user_prompt(
        normalized_message,
        document_id=document_id,
        has_processed_documents_hint=has_processed_documents_hint,
        conversation_history=conversation_history,
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

        if turn.function_calls:
            tool_result_blocks: list[str] = []
            for call in turn.function_calls:
                tool_name, arguments = _prepare_tool_arguments(
                    call,
                    document_id=document_id,
                    top_k=top_k,
                )
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
                    failure_response = _build_tool_failure_response(
                        normalized_message,
                        tool_result,
                        used_tools=used_tools,
                        tool_activities=tool_activities,
                    )
                    return _finalize_agent_response(
                        failure_response,
                        session_id=resolved_session_id,
                        user_message=normalized_message,
                        persist_memory=persist_memory,
                        is_new_session=is_new_session,
                    )

                _accumulate_tool_result(accumulated, tool_name, tool_result)
                tool_result_blocks.append(
                    _format_tool_result_for_prompt(tool_name, tool_result)
                )

            user_prompt = f"{user_prompt}\n\n" + "\n\n".join(tool_result_blocks)
            continue

        if turn.text:
            if used_tools:
                tool_response = _build_final_tool_response(
                    normalized_message,
                    turn.text,
                    accumulated,
                    used_tools=used_tools,
                    tool_activities=tool_activities,
                )
                return _finalize_agent_response(
                    tool_response,
                    session_id=resolved_session_id,
                    user_message=normalized_message,
                    persist_memory=persist_memory,
                    is_new_session=is_new_session,
                )
            direct_response = AgentChatResponse(
                message=normalized_message,
                answer=turn.text,
                citations=[],
                insufficient_evidence=False,
                used_tools=used_tools,
                tool_activities=tool_activities,
                direct_answer=True,
                used_chunk_count=0,
            )
            return _finalize_agent_response(
                direct_response,
                session_id=resolved_session_id,
                user_message=normalized_message,
                persist_memory=persist_memory,
                is_new_session=is_new_session,
            )

    if used_tools:
        fallback_response = _build_fallback_tool_response(
            normalized_message,
            accumulated,
            used_tools=used_tools,
            tool_activities=tool_activities,
        )
        return _finalize_agent_response(
            fallback_response,
            session_id=resolved_session_id,
            user_message=normalized_message,
            persist_memory=persist_memory,
            is_new_session=is_new_session,
        )

    raise AgentError("Agent exceeded the maximum number of tool rounds.")
