"""Pydantic models for chat sessions and persisted messages."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agent import ToolActivity
from app.schemas.operational import OperationalSourceBundle
from app.schemas.rag import RagCitation


class ChatSessionSummary(BaseModel):
    id: UUID
    title: str | None = None
    document_id: UUID | None = None
    message_count: int = 0
    preview: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionSummary] = Field(default_factory=list)
    total: int = 0


class ChatMessageRecord(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: list[RagCitation] = Field(default_factory=list)
    operational_sources: list[OperationalSourceBundle] = Field(default_factory=list)
    tool_activities: list[ToolActivity] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)
    direct_answer: bool = False
    insufficient_evidence: bool = False
    used_chunk_count: int = 0
    created_at: datetime


class ChatSessionDetail(BaseModel):
    id: UUID
    title: str | None = None
    document_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageRecord] = Field(default_factory=list)


class CreateChatSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    document_id: UUID | None = None
