"""Smoke tests for document upload and list endpoints.

Purpose: Verifies /health, /documents, and /documents/upload behavior end-to-end.
Interactions: Uses TestClient against app.main. Requires DATABASE_URL, the
documents table (infra/init-db.sql), and sample-data/test-upload.pdf.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SAMPLE_PDF = (
    Path(__file__).resolve().parents[3] / "sample-data" / "test-upload.pdf"
)


@contextmanager
def uploaded_sample_document(client: TestClient) -> Iterator[dict]:
    with SAMPLE_PDF.open("rb") as pdf_file:
        upload_response = client.post(
            "/documents/upload",
            files={"file": ("test-upload.pdf", pdf_file, "application/pdf")},
        )

    assert upload_response.status_code == 201, upload_response.text
    uploaded = upload_response.json()

    try:
        yield uploaded
    finally:
        client.delete(f"/documents/{uploaded['id']}")


def test_health_still_works() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"healthy", "degraded"}


def test_list_documents_returns_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/documents")
    assert response.status_code == 200
    payload = response.json()
    assert "documents" in payload
    assert "total" in payload
    assert isinstance(payload["documents"], list)


def test_upload_pdf_and_list() -> None:
    with TestClient(app) as client:
        with uploaded_sample_document(client) as uploaded:
            assert uploaded["original_filename"] == "test-upload.pdf"
            assert uploaded["status"] == "uploaded"

            list_response = client.get("/documents")
            assert list_response.status_code == 200
            documents = list_response.json()["documents"]
            assert any(item["id"] == uploaded["id"] for item in documents)


def test_reject_non_pdf_upload() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents/upload",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_get_document_file() -> None:
    with TestClient(app) as client:
        with uploaded_sample_document(client) as uploaded:
            file_response = client.get(f"/documents/{uploaded['id']}/file")
            assert file_response.status_code == 200
            assert file_response.headers["content-type"].startswith("application/pdf")
            assert file_response.headers["content-disposition"].startswith("inline")
            assert file_response.content.startswith(b"%PDF")


def test_delete_document() -> None:
    with TestClient(app) as client:
        with uploaded_sample_document(client) as uploaded:
            document_id = uploaded["id"]

            delete_response = client.delete(f"/documents/{document_id}")
            assert delete_response.status_code == 200
            assert delete_response.json()["deleted"] is True

            list_response = client.get("/documents")
            documents = list_response.json()["documents"]
            assert not any(item["id"] == document_id for item in documents)

            file_response = client.get(f"/documents/{document_id}/file")
            assert file_response.status_code == 404
