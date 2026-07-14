"""Pydantic models for the agent chat API."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.operational import OperationalSourceBundle
from app.schemas.rag import RagCitation


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    document_id: UUID | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)


class ToolActivity(BaseModel):
    tool_name: str
    status: str
    summary: str
    error: str | None = None


class AgentChatResponse(BaseModel):
    message: str
    answer: str
    citations: list[RagCitation] = Field(default_factory=list)
    operational_sources: list[OperationalSourceBundle] = Field(default_factory=list)
    insufficient_evidence: bool = False
    used_tools: list[str] = Field(default_factory=list)
    tool_activities: list[ToolActivity] = Field(default_factory=list)
    direct_answer: bool = False
    used_chunk_count: int = 0
