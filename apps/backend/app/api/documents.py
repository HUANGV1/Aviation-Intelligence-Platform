"""HTTP routes for document upload, library access, and processing.

Purpose: Exposes upload/list/view/delete routes plus PDF processing and chunk
inspection endpoints for Week 3.
Interactions: Mounted by main.py. Delegates to document_storage.py,
document_repository.py, chunk_repository.py, and document_processing.py.
Called by the frontend through lib/api.ts.
"""

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.schemas.chunk import ChunkListResponse, ProcessDocumentResponse
from app.schemas.document import (
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.chunk_repository import list_chunks_for_document
from app.services.document_processing import DocumentProcessingError, process_document
from app.services.document_repository import (
    create_document,
    delete_document,
    get_document,
    list_documents,
)
from app.services.document_storage import (
    delete_local_pdf,
    resolve_document_path,
    save_pdf_upload,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentResponse:
    stored_filename, original_filename, destination = await save_pdf_upload(file)

    try:
        return create_document(
            filename=stored_filename,
            original_filename=original_filename,
            file_path=str(destination),
        )
    except RuntimeError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("", response_model=DocumentListResponse)
def get_documents() -> DocumentListResponse:
    try:
        documents = list_documents()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return DocumentListResponse(documents=documents, total=len(documents))


@router.get("/{document_id}/file")
def get_document_file(document_id: UUID) -> FileResponse:
    try:
        document = get_document(document_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    file_path = resolve_document_path(document.file_path)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=document.original_filename,
        content_disposition_type="inline",
    )


@router.post("/{document_id}/process", response_model=ProcessDocumentResponse)
def process_document_by_id(document_id: UUID) -> ProcessDocumentResponse:
    try:
        page_count, chunk_count = process_document(document_id)
    except DocumentProcessingError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if message == "Document not found."
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ProcessDocumentResponse(
        document_id=document_id,
        status="processed",
        page_count=page_count,
        chunk_count=chunk_count,
    )


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
def get_document_chunks(document_id: UUID) -> ChunkListResponse:
    try:
        document = get_document(document_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    try:
        chunks = list_chunks_for_document(document_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return ChunkListResponse(
        document_id=document_id,
        chunks=chunks,
        total=len(chunks),
    )


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
def remove_document(document_id: UUID) -> DeleteDocumentResponse:
    try:
        document = delete_document(document_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    delete_local_pdf(document.file_path)
    return DeleteDocumentResponse(id=document.id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_by_id(document_id: UUID) -> DocumentResponse:
    try:
        document = get_document(document_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document
