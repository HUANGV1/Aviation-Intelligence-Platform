"""Tests for chat session and message repositories."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.chat import ChatMessageRecord
from app.services.agent_service import _derive_session_title
from app.services.chat_message_repository import get_recent_messages_for_memory
from app.services.chat_session_repository import create_session, delete_session, list_sessions


@patch("app.services.chat_session_repository.get_engine")
def test_create_session_returns_summary(mock_get_engine) -> None:
    session_id = uuid4()
    now = datetime.now(tz=UTC)
    connection = MagicMock()
    mock_get_engine.return_value.connect.return_value.__enter__.return_value = connection
    connection.execute.return_value.one.return_value = MagicMock(
        id=session_id,
        title=None,
        document_id=None,
        created_at=now,
        updated_at=now,
    )

    summary = create_session()

    assert summary.id == session_id
    assert summary.message_count == 0
    connection.commit.assert_called_once()


@patch("app.services.chat_session_repository.get_engine")
def test_delete_session_returns_true_when_deleted(mock_get_engine) -> None:
    connection = MagicMock()
    mock_get_engine.return_value.connect.return_value.__enter__.return_value = connection
    connection.execute.return_value.one_or_none.return_value = MagicMock(id=uuid4())

    deleted = delete_session(uuid4())

    assert deleted is True
    connection.commit.assert_called_once()


@patch("app.services.chat_session_repository.get_engine")
def test_list_sessions_returns_rows(mock_get_engine) -> None:
    session_id = uuid4()
    now = datetime.now(tz=UTC)
    connection = MagicMock()
    mock_get_engine.return_value.connect.return_value.__enter__.return_value = connection
    connection.execute.return_value.all.return_value = [
        MagicMock(
            id=session_id,
            title="METAR for KJFK?",
            document_id=None,
            created_at=now,
            updated_at=now,
            message_count=2,
            preview="KJFK is VFR.",
        )
    ]

    sessions = list_sessions()

    assert len(sessions) == 1
    assert sessions[0].id == session_id
    assert sessions[0].message_count == 2
    assert sessions[0].preview == "KJFK is VFR."


@patch("app.services.chat_message_repository.get_engine")
def test_get_recent_messages_for_memory_limits_turns(mock_get_engine) -> None:
    session_id = uuid4()
    now = datetime.now(tz=UTC)
    connection = MagicMock()
    mock_get_engine.return_value.connect.return_value.__enter__.return_value = connection
    connection.execute.return_value.all.return_value = [
        MagicMock(
            id=uuid4(),
            session_id=session_id,
            role="assistant",
            content="Latest answer",
            citations=[],
            operational_sources=[],
            tool_activities=[],
            used_tools=[],
            direct_answer=True,
            insufficient_evidence=False,
            used_chunk_count=0,
            created_at=now,
        ),
        MagicMock(
            id=uuid4(),
            session_id=session_id,
            role="user",
            content="Latest question",
            citations=[],
            operational_sources=[],
            tool_activities=[],
            used_tools=[],
            direct_answer=False,
            insufficient_evidence=False,
            used_chunk_count=0,
            created_at=now,
        ),
    ]

    messages = get_recent_messages_for_memory(session_id, max_turns=5)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    connection.execute.assert_called_once()


def test_derive_session_title_truncates_long_messages() -> None:
    title = _derive_session_title("A" * 80)

    assert len(title) <= 60
    assert title.endswith("…")
