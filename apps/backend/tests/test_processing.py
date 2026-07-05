"""Integration tests for PDF processing and chunk endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SAMPLE_PDF = (
    Path(__file__).resolve().parents[3] / "sample-data" / "test-process.pdf"
)


def _upload_sample(client: TestClient) -> dict:
    with SAMPLE_PDF.open("rb") as pdf_file:
        response = client.post(
            "/documents/upload",
            files={"file": ("test-process.pdf", pdf_file, "application/pdf")},
        )
    assert response.status_code == 201, response.text
    return response.json()


def test_process_document_creates_chunks() -> None:
    with TestClient(app) as client:
        uploaded = _upload_sample(client)
        document_id = uploaded["id"]

        process_response = client.post(f"/documents/{document_id}/process")
        assert process_response.status_code == 200, process_response.text

        payload = process_response.json()
        assert payload["status"] == "processed"
        assert payload["page_count"] >= 1
        assert payload["chunk_count"] >= 1

        document_response = client.get(f"/documents/{document_id}")
        assert document_response.status_code == 200
        document = document_response.json()
        assert document["status"] == "processed"
        assert document["page_count"] >= 1

        chunks_response = client.get(f"/documents/{document_id}/chunks")
        assert chunks_response.status_code == 200
        chunks_payload = chunks_response.json()
        assert chunks_payload["total"] == payload["chunk_count"]
        assert len(chunks_payload["chunks"]) == payload["chunk_count"]
        assert chunks_payload["chunks"][0]["chunk_index"] == 0


def test_reprocess_does_not_duplicate_chunks() -> None:
    with TestClient(app) as client:
        uploaded = _upload_sample(client)
        document_id = uploaded["id"]

        first = client.post(f"/documents/{document_id}/process")
        assert first.status_code == 200
        first_count = first.json()["chunk_count"]

        second = client.post(f"/documents/{document_id}/process")
        assert second.status_code == 400

        chunks_response = client.get(f"/documents/{document_id}/chunks")
        assert chunks_response.status_code == 200
        assert chunks_response.json()["total"] == first_count


def test_process_missing_document_returns_404() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents/00000000-0000-0000-0000-000000000099/process"
        )
    assert response.status_code == 404
