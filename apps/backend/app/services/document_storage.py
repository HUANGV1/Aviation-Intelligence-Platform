"""Local filesystem handling for uploaded PDF files.

Purpose: Validates PDF uploads, enforces size limits, and saves files under uploads/.
Interactions: Called by api/documents.py on upload. Uses upload settings from
config.py. Writes bytes to disk; metadata is persisted separately by
document_repository.py.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import settings

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "text/x-pdf",
}


def ensure_upload_dir() -> Path:
    upload_dir = settings.upload_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def validate_pdf_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A filename is required.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )


async def save_pdf_upload(file: UploadFile) -> tuple[str, str, Path]:
    validate_pdf_upload(file)

    upload_dir = ensure_upload_dir()
    stored_filename = f"{uuid.uuid4()}.pdf"
    destination = upload_dir / stored_filename

    max_bytes = settings.max_upload_bytes
    total_bytes = 0
    header = b""

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break

                if len(header) < 5:
                    header += chunk[: 5 - len(header)]

                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {settings.max_upload_mb} MB upload limit.",
                    )

                output.write(chunk)
    except HTTPException:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file.",
        ) from exc
    finally:
        await file.close()

    if total_bytes == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if not header.startswith(b"%PDF"):
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only valid PDF files are allowed.",
        )

    return stored_filename, file.filename, destination


def _candidate_under_upload_dir(file_path: str) -> Path:
    """Map a stored path to the current upload dir (handles legacy absolute paths)."""
    candidate = Path(file_path)
    upload_root = settings.upload_path.resolve()

    if not candidate.is_absolute():
        return (settings.upload_path / candidate).resolve()

    resolved = candidate.resolve()
    try:
        resolved.relative_to(upload_root)
        return resolved
    except ValueError:
        # Legacy rows may store a host absolute path from a different environment.
        return (settings.upload_path / candidate.name).resolve()


def resolve_document_path(file_path: str) -> Path:
    """Resolve and validate a stored PDF path is inside the upload directory."""
    resolved = _candidate_under_upload_dir(file_path)
    upload_root = settings.upload_path.resolve()

    try:
        resolved.relative_to(upload_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found.",
        ) from exc

    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found.",
        )

    return resolved


def delete_local_pdf(file_path: str) -> None:
    """Delete a PDF from disk; missing files are ignored."""
    resolved = _candidate_under_upload_dir(file_path)
    upload_root = settings.upload_path.resolve()

    try:
        resolved.relative_to(upload_root)
    except ValueError:
        return

    if resolved.is_file():
        resolved.unlink(missing_ok=True)