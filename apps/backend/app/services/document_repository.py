"""Database access layer for document metadata.

Purpose: Inserts and queries rows in the Supabase documents table (defined in
infra/init-db.sql).
Interactions: Uses get_engine() from database.py and returns schemas/document.py
models. Called by api/documents.py; does not read PDF files from disk.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_engine
from app.schemas.document import DocumentResponse


def _row_to_document(row) -> DocumentResponse:
    return DocumentResponse(
        id=row.id,
        filename=row.filename,
        original_filename=row.original_filename,
        source_type=row.source_type,
        acquisition_mode=row.acquisition_mode,
        status=row.status,
        file_path=row.file_path,
        page_count=row.page_count,
        source_url=row.source_url,
        uploaded_at=row.uploaded_at,
        retrieved_at=row.retrieved_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_document(
    *,
    filename: str,
    original_filename: str,
    file_path: str,
) -> DocumentResponse:
    query = text(
        """
        INSERT INTO documents (
            filename,
            original_filename,
            source_type,
            acquisition_mode,
            status,
            file_path
        )
        VALUES (
            :filename,
            :original_filename,
            'upload',
            'user_upload',
            'uploaded',
            :file_path
        )
        RETURNING
            id,
            filename,
            original_filename,
            source_type,
            acquisition_mode,
            status,
            file_path,
            page_count,
            source_url,
            uploaded_at,
            retrieved_at,
            created_at,
            updated_at
        """
    )

    try:
        with get_engine().connect() as connection:
            result = connection.execute(
                query,
                {
                    "filename": filename,
                    "original_filename": original_filename,
                    "file_path": file_path,
                },
            )
            row = result.one()
            connection.commit()
            return _row_to_document(row)
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to save document metadata.") from exc


def list_documents() -> list[DocumentResponse]:
    query = text(
        """
        SELECT
            id,
            filename,
            original_filename,
            source_type,
            acquisition_mode,
            status,
            file_path,
            page_count,
            source_url,
            uploaded_at,
            retrieved_at,
            created_at,
            updated_at
        FROM documents
        ORDER BY created_at DESC
        """
    )

    try:
        with get_engine().connect() as connection:
            rows = connection.execute(query).all()
            return [_row_to_document(row) for row in rows]
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to load documents.") from exc


def get_document(document_id: UUID) -> DocumentResponse | None:
    query = text(
        """
        SELECT
            id,
            filename,
            original_filename,
            source_type,
            acquisition_mode,
            status,
            file_path,
            page_count,
            source_url,
            uploaded_at,
            retrieved_at,
            created_at,
            updated_at
        FROM documents
        WHERE id = :document_id
        """
    )

    try:
        with get_engine().connect() as connection:
            row = connection.execute(query, {"document_id": document_id}).one_or_none()
            if row is None:
                return None
            return _row_to_document(row)
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to load document.") from exc


def delete_document(document_id: UUID) -> DocumentResponse | None:
    query = text(
        """
        DELETE FROM documents
        WHERE id = :document_id
        RETURNING
            id,
            filename,
            original_filename,
            source_type,
            acquisition_mode,
            status,
            file_path,
            page_count,
            source_url,
            uploaded_at,
            retrieved_at,
            created_at,
            updated_at
        """
    )

    try:
        with get_engine().connect() as connection:
            row = connection.execute(query, {"document_id": document_id}).one_or_none()
            connection.commit()
            if row is None:
                return None
            return _row_to_document(row)
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to delete document.") from exc


def update_document_status(document_id: UUID, status: str) -> DocumentResponse | None:
    query = text(
        """
        UPDATE documents
        SET status = :status
        WHERE id = :document_id
        RETURNING
            id,
            filename,
            original_filename,
            source_type,
            acquisition_mode,
            status,
            file_path,
            page_count,
            source_url,
            uploaded_at,
            retrieved_at,
            created_at,
            updated_at
        """
    )

    try:
        with get_engine().connect() as connection:
            row = connection.execute(
                query,
                {"document_id": document_id, "status": status},
            ).one_or_none()
            connection.commit()
            if row is None:
                return None
            return _row_to_document(row)
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to update document status.") from exc


def update_document_page_count(document_id: UUID, page_count: int) -> DocumentResponse | None:
    query = text(
        """
        UPDATE documents
        SET page_count = :page_count
        WHERE id = :document_id
        RETURNING
            id,
            filename,
            original_filename,
            source_type,
            acquisition_mode,
            status,
            file_path,
            page_count,
            source_url,
            uploaded_at,
            retrieved_at,
            created_at,
            updated_at
        """
    )

    try:
        with get_engine().connect() as connection:
            row = connection.execute(
                query,
                {"document_id": document_id, "page_count": page_count},
            ).one_or_none()
            connection.commit()
            if row is None:
                return None
            return _row_to_document(row)
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to update document page count.") from exc
