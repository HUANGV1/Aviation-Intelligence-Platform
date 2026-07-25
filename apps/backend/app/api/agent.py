"""HTTP routes for the unified agent chat interface."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.schemas.chat import (
    ChatSessionDetail,
    ChatSessionListResponse,
    CreateChatSessionRequest,
)
from app.services.agent_service import AgentError, run_agent_chat
from app.services.chat_session_repository import (
    ChatSessionError,
    create_session,
    delete_session,
    get_session,
    list_sessions,
)
from app.services.llm_service import LLMQuotaError

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/sessions", response_model=ChatSessionDetail, status_code=201)
def create_chat_session(request: CreateChatSessionRequest) -> ChatSessionDetail:
    try:
        summary = create_session(
            title=request.title,
            document_id=request.document_id,
        )
        detail = get_session(summary.id)
        if detail is None:
            raise ChatSessionError("Failed to load created chat session.")
        return detail
    except ChatSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_chat_sessions() -> ChatSessionListResponse:
    try:
        sessions = list_sessions()
        return ChatSessionListResponse(sessions=sessions, total=len(sessions))
    except ChatSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(session_id: UUID) -> ChatSessionDetail:
    try:
        detail = get_session(session_id)
    except ChatSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )
    return detail


@router.delete("/sessions/{session_id}", status_code=204)
def delete_chat_session(session_id: UUID) -> None:
    try:
        deleted = delete_session(session_id)
    except ChatSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(request: AgentChatRequest) -> AgentChatResponse:
    try:
        return run_agent_chat(
            request.message,
            session_id=request.session_id,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except LLMQuotaError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except AgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
