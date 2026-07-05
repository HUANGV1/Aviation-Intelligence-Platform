"""Document processing orchestration service.

Purpose: Coordinates PDF extraction, chunking, embedding, persistence, and status updates.
Interactions: Uses document_storage, pdf_extraction, chunking, embedding_service,
chunk_repository, and document_repository. Called by POST /documents/{id}/process.
"""

import logging
from uuid import UUID

from app.services.chunk_repository import (
    delete_chunks_for_document,
    insert_chunks,
    update_chunk_embeddings,
)
from app.services.chunking import chunk_pages
from app.services.document_repository import (
    get_document,
    update_document_page_count,
    update_document_status,
)
from app.services.document_storage import resolve_document_path
from app.services.embedding_service import (
    EmbeddingError,
    embed_texts,
    format_document_text,
)
from app.services.pdf_extraction import PdfExtractionError, extract_pdf_text

logger = logging.getLogger(__name__)

PROCESSABLE_STATUSES = {"uploaded", "failed", "cancelled"}


class DocumentProcessingError(Exception):
    """Raised when a document cannot be processed."""


class DocumentProcessingCancelled(Exception):
    """Raised when a document processing run is cancelled."""


def _raise_if_cancelled(document_id: UUID) -> None:
    document = get_document(document_id)
    if document is not None and document.status == "cancelled":
        raise DocumentProcessingCancelled("Document processing was cancelled.")


def process_document(document_id: UUID) -> tuple[int, int]:
    document = get_document(document_id)
    if document is None:
        raise DocumentProcessingError("Document not found.")

    if document.status not in PROCESSABLE_STATUSES:
        raise DocumentProcessingError(
            f"Document cannot be processed from status '{document.status}'."
        )

    update_document_status(document_id, "processing")

    try:
        file_path = resolve_document_path(document.file_path)
        extraction = extract_pdf_text(file_path)
        _raise_if_cancelled(document_id)

        if not extraction.pages:
            raise DocumentProcessingError(
                "No extractable text found in this PDF. It may be scanned or image-only; "
                "OCR is not supported in the MVP."
            )

        delete_chunks_for_document(document_id)
        chunks = chunk_pages(extraction.pages)
        _raise_if_cancelled(document_id)
        chunk_count = insert_chunks(document_id, chunks)
        update_document_page_count(document_id, extraction.page_count)
        _raise_if_cancelled(document_id)

        embedding_inputs = [
            format_document_text(
                text=chunk.text,
                title=chunk.section_title or document.original_filename,
            )
            for chunk in chunks
        ]

        try:
            embeddings = embed_texts(embedding_inputs)
        except EmbeddingError as exc:
            raise DocumentProcessingError(str(exc)) from exc
        _raise_if_cancelled(document_id)

        updated_embeddings = update_chunk_embeddings(
            document_id,
            chunk_indexes=[chunk.chunk_index for chunk in chunks],
            embeddings=embeddings,
        )
        _raise_if_cancelled(document_id)
        if updated_embeddings != chunk_count:
            raise DocumentProcessingError(
                "Document chunks changed during embedding. Please process the document again."
            )

        update_document_status(document_id, "processed")

        return extraction.page_count, chunk_count
    except DocumentProcessingCancelled:
        delete_chunks_for_document(document_id)
        update_document_status(document_id, "cancelled")
        raise
    except DocumentProcessingError:
        update_document_status(document_id, "failed")
        raise
    except PdfExtractionError as exc:
        logger.warning("PDF extraction failed for %s: %s", document_id, exc)
        update_document_status(document_id, "failed")
        raise DocumentProcessingError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Document processing failed for %s", document_id)
        update_document_status(document_id, "failed")
        raise DocumentProcessingError("Document processing failed.") from exc
