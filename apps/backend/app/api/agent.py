"""HTTP routes for the unified agent chat interface."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.agent_service import AgentError, run_agent_chat
from app.services.llm_service import LLMQuotaError

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(request: AgentChatRequest) -> AgentChatResponse:
    try:
        return run_agent_chat(
            request.message,
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
