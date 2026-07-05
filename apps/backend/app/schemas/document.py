"""Pydantic response models for document API endpoints.

Purpose: Defines the JSON shape for single documents and document list responses.
Interactions: Used by api/documents.py for validation/serialization and by
document_repository.py when mapping SQL rows. Mirrors types in frontend lib/api.ts.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    source_type: str
    acquisition_mode: str
    status: str
    file_path: str
    page_count: int | None = None
    source_url: str | None = None
    uploaded_at: datetime
    retrieved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse] = Field(default_factory=list)
    total: int


class DeleteDocumentResponse(BaseModel):
    id: UUID
    deleted: bool = True
    message: str = "Document deleted."
