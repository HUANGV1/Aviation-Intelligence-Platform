"""Pydantic models for semantic search API requests and responses."""

from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_id: UUID | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)


class SearchResultItem(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    text: str
    page_number: int | None = None
    section_title: str | None = None
    similarity: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem] = Field(default_factory=list)
    total: int
