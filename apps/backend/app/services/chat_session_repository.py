"""Database access layer for chat_sessions."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine
from app.schemas.chat import ChatSessionDetail, ChatSessionSummary


class ChatSessionError(Exception):
    """Raised when chat session persistence fails."""


def _row_to_summary(row) -> ChatSessionSummary:
    return ChatSessionSummary(
        id=row.id,
        title=row.title,
        document_id=row.document_id,
        message_count=int(row.message_count or 0),
        preview=row.preview,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_session(
    *,
    title: str | None = None,
    document_id: UUID | None = None,
) -> ChatSessionSummary:
    query = text(
        """
        INSERT INTO chat_sessions (title, document_id)
        VALUES (:title, :document_id)
        RETURNING
            id,
            title,
            document_id,
            created_at,
            updated_at
        """
    )

    try:
        with get_engine().connect() as connection:
            row = connection.execute(
                query,
                {"title": title, "document_id": document_id},
            ).one()
            connection.commit()
            return ChatSessionSummary(
                id=row.id,
                title=row.title,
                document_id=row.document_id,
                message_count=0,
                preview=None,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
    except SQLAlchemyError as exc:
        raise ChatSessionError("Failed to create chat session.") from exc


def list_sessions(*, limit: int = 50) -> list[ChatSessionSummary]:
    query = text(
        """
        SELECT
            s.id,
            s.title,
            s.document_id,
            s.created_at,
            s.updated_at,
            COUNT(m.id) AS message_count,
            (
                SELECT content
                FROM chat_messages
                WHERE session_id = s.id
                ORDER BY created_at DESC
                LIMIT 1
            ) AS preview
        FROM chat_sessions s
        LEFT JOIN chat_messages m ON m.session_id = s.id
        GROUP BY s.id, s.title, s.document_id, s.created_at, s.updated_at
        ORDER BY s.updated_at DESC
        LIMIT :limit
        """
    )

    try:
        with get_engine().connect() as connection:
            rows = connection.execute(query, {"limit": limit}).all()
            return [_row_to_summary(row) for row in rows]
    except SQLAlchemyError as exc:
        raise ChatSessionError("Failed to list chat sessions.") from exc


def get_session(session_id: UUID) -> ChatSessionDetail | None:
    session_query = text(
        """
        SELECT id, title, document_id, created_at, updated_at
        FROM chat_sessions
        WHERE id = :session_id
        """
    )

    try:
        with get_engine().connect() as connection:
            session_row = connection.execute(
                session_query,
                {"session_id": session_id},
            ).one_or_none()
            if session_row is None:
                return None

            from app.services.chat_message_repository import list_messages_for_session

            messages = list_messages_for_session(session_id, connection=connection)
            return ChatSessionDetail(
                id=session_row.id,
                title=session_row.title,
                document_id=session_row.document_id,
                created_at=session_row.created_at,
                updated_at=session_row.updated_at,
                messages=messages,
            )
    except SQLAlchemyError as exc:
        raise ChatSessionError("Failed to load chat session.") from exc


def session_exists(session_id: UUID) -> bool:
    query = text(
        """
        SELECT 1
        FROM chat_sessions
        WHERE id = :session_id
        """
    )

    try:
        with get_engine().connect() as connection:
            row = connection.execute(query, {"session_id": session_id}).one_or_none()
            return row is not None
    except SQLAlchemyError:
        return False


def update_session_title(session_id: UUID, title: str) -> None:
    query = text(
        """
        UPDATE chat_sessions
        SET title = :title
        WHERE id = :session_id
        """
    )

    try:
        with get_engine().connect() as connection:
            connection.execute(
                query,
                {"session_id": session_id, "title": title},
            )
            connection.commit()
    except SQLAlchemyError as exc:
        raise ChatSessionError("Failed to update chat session title.") from exc


def touch_session(session_id: UUID) -> None:
    query = text(
        """
        UPDATE chat_sessions
        SET updated_at = NOW()
        WHERE id = :session_id
        """
    )

    try:
        with get_engine().connect() as connection:
            connection.execute(query, {"session_id": session_id})
            connection.commit()
    except SQLAlchemyError as exc:
        raise ChatSessionError("Failed to update chat session activity.") from exc


def delete_session(session_id: UUID) -> bool:
    query = text(
        """
        DELETE FROM chat_sessions
        WHERE id = :session_id
        RETURNING id
        """
    )

    try:
        with get_engine().connect() as connection:
            row = connection.execute(query, {"session_id": session_id}).one_or_none()
            connection.commit()
            return row is not None
    except SQLAlchemyError as exc:
        raise ChatSessionError("Failed to delete chat session.") from exc


def update_session_metadata(session_id: UUID, metadata: dict) -> None:
    query = text(
        """
        UPDATE chat_sessions
        SET metadata = CAST(:metadata AS jsonb)
        WHERE id = :session_id
        """
    )

    try:
        with get_engine().connect() as connection:
            connection.execute(
                query,
                {
                    "session_id": session_id,
                    "metadata": json.dumps(metadata),
                },
            )
            connection.commit()
    except SQLAlchemyError as exc:
        raise ChatSessionError("Failed to update chat session metadata.") from exc
