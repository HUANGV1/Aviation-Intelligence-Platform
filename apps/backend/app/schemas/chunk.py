"""Pydantic models for document chunk API responses.

Purpose: Defines JSON shapes for chunk inspection and processing summaries.
Interactions: Used by api/documents.py and chunk_repository.py. Mirrors types
in frontend lib/api.ts.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    page_number: int | None = None
    section_title: str | None = None
    token_count: int
    created_at: datetime


class ChunkListResponse(BaseModel):
    document_id: UUID
    chunks: list[ChunkResponse] = Field(default_factory=list)
    total: int


class ProcessDocumentResponse(BaseModel):
    document_id: UUID
    status: str
    page_count: int
    chunk_count: int
    message: str = "Document processed successfully."
