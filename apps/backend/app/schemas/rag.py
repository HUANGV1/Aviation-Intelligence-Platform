"""Pydantic models for cited RAG query API requests and responses."""

from uuid import UUID

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_id: UUID | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)


class RagCitation(BaseModel):
    source_id: str
    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    text: str
    page_number: int | None = None
    section_title: str | None = None
    similarity: float


class RagQueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[RagCitation] = Field(default_factory=list)
    insufficient_evidence: bool = False
    used_chunk_count: int = 0
