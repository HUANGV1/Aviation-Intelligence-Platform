"""Database access layer for chat_messages."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine
from app.schemas.agent import ToolActivity
from app.schemas.chat import ChatMessageRecord
from app.schemas.operational import OperationalSourceBundle
from app.schemas.rag import RagCitation


class ChatMessageError(Exception):
    """Raised when chat message persistence fails."""


def _deserialize_citations(raw: object) -> list[RagCitation]:
    if not isinstance(raw, list):
        return []
    citations: list[RagCitation] = []
    for item in raw:
        try:
            citations.append(RagCitation.model_validate(item))
        except Exception:
            continue
    return citations


def _deserialize_operational_sources(raw: object) -> list[OperationalSourceBundle]:
    if not isinstance(raw, list):
        return []
    bundles: list[OperationalSourceBundle] = []
    for item in raw:
        try:
            bundles.append(OperationalSourceBundle.model_validate(item))
        except Exception:
            continue
    return bundles


def _deserialize_tool_activities(raw: object) -> list[ToolActivity]:
    if not isinstance(raw, list):
        return []
    activities: list[ToolActivity] = []
    for item in raw:
        try:
            activities.append(ToolActivity.model_validate(item))
        except Exception:
            continue
    return activities


def _row_to_message(row) -> ChatMessageRecord:
    return ChatMessageRecord(
        id=row.id,
        session_id=row.session_id,
        role=row.role,
        content=row.content,
        citations=_deserialize_citations(row.citations),
        operational_sources=_deserialize_operational_sources(row.operational_sources),
        tool_activities=_deserialize_tool_activities(row.tool_activities),
        used_tools=list(row.used_tools or []),
        direct_answer=bool(row.direct_answer),
        insufficient_evidence=bool(row.insufficient_evidence),
        used_chunk_count=int(row.used_chunk_count or 0),
        created_at=row.created_at,
    )


def insert_message(
    *,
    session_id: UUID,
    role: str,
    content: str,
    citations: list[RagCitation] | None = None,
    operational_sources: list[OperationalSourceBundle] | None = None,
    tool_activities: list[ToolActivity] | None = None,
    used_tools: list[str] | None = None,
    direct_answer: bool = False,
    insufficient_evidence: bool = False,
    used_chunk_count: int = 0,
) -> ChatMessageRecord:
    query = text(
        """
        INSERT INTO chat_messages (
            session_id,
            role,
            content,
            citations,
            operational_sources,
            tool_activities,
            used_tools,
            direct_answer,
            insufficient_evidence,
            used_chunk_count
        )
        VALUES (
            :session_id,
            :role,
            :content,
            CAST(:citations AS jsonb),
            CAST(:operational_sources AS jsonb),
            CAST(:tool_activities AS jsonb),
            :used_tools,
            :direct_answer,
            :insufficient_evidence,
            :used_chunk_count
        )
        RETURNING
            id,
            session_id,
            role,
            content,
            citations,
            operational_sources,
            tool_activities,
            used_tools,
            direct_answer,
            insufficient_evidence,
            used_chunk_count,
            created_at
        """
    )

    payload = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "citations": json.dumps(
            [item.model_dump(mode="json") for item in (citations or [])]
        ),
        "operational_sources": json.dumps(
            [item.model_dump(mode="json") for item in (operational_sources or [])]
        ),
        "tool_activities": json.dumps(
            [item.model_dump(mode="json") for item in (tool_activities or [])]
        ),
        "used_tools": used_tools or [],
        "direct_answer": direct_answer,
        "insufficient_evidence": insufficient_evidence,
        "used_chunk_count": used_chunk_count,
    }

    try:
        with get_engine().connect() as connection:
            row = connection.execute(query, payload).one()
            connection.execute(
                text(
                    """
                    UPDATE chat_sessions
                    SET updated_at = NOW()
                    WHERE id = :session_id
                    """
                ),
                {"session_id": session_id},
            )
            connection.commit()
            return _row_to_message(row)
    except SQLAlchemyError as exc:
        raise ChatMessageError("Failed to insert chat message.") from exc


def list_messages_for_session(
    session_id: UUID,
    *,
    connection: Connection | None = None,
) -> list[ChatMessageRecord]:
    query = text(
        """
        SELECT
            id,
            session_id,
            role,
            content,
            citations,
            operational_sources,
            tool_activities,
            used_tools,
            direct_answer,
            insufficient_evidence,
            used_chunk_count,
            created_at
        FROM chat_messages
        WHERE session_id = :session_id
        ORDER BY created_at ASC
        """
    )

    try:
        if connection is not None:
            rows = connection.execute(query, {"session_id": session_id}).all()
            return [_row_to_message(row) for row in rows]

        with get_engine().connect() as owned_connection:
            rows = owned_connection.execute(query, {"session_id": session_id}).all()
            return [_row_to_message(row) for row in rows]
    except SQLAlchemyError as exc:
        raise ChatMessageError("Failed to list chat messages.") from exc


def get_recent_messages_for_memory(
    session_id: UUID,
    *,
    max_turns: int,
) -> list[ChatMessageRecord]:
    max_messages = max_turns * 2
    query = text(
        """
        SELECT
            id,
            session_id,
            role,
            content,
            citations,
            operational_sources,
            tool_activities,
            used_tools,
            direct_answer,
            insufficient_evidence,
            used_chunk_count,
            created_at
        FROM chat_messages
        WHERE session_id = :session_id
          AND role IN ('user', 'assistant')
        ORDER BY created_at DESC
        LIMIT :max_messages
        """
    )

    try:
        with get_engine().connect() as connection:
            rows = connection.execute(
                query,
                {"session_id": session_id, "max_messages": max_messages},
            ).all()
            messages = [_row_to_message(row) for row in reversed(rows)]
            return messages
    except SQLAlchemyError as exc:
        raise ChatMessageError("Failed to load recent chat messages.") from exc
