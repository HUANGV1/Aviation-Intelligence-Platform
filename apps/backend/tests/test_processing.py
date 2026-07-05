"""Integration tests for PDF processing and chunk endpoints."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

SAMPLE_PDF = (
    Path(__file__).resolve().parents[3] / "sample-data" / "test-process.pdf"
)


def _fake_embeddings(count: int) -> list[list[float]]:
    return [[float(index) / 1000.0] * 768 for index in range(count)]


@contextmanager
def uploaded_sample_document(client: TestClient) -> Iterator[dict]:
    with SAMPLE_PDF.open("rb") as pdf_file:
        response = client.post(
            "/documents/upload",
            files={"file": ("test-process.pdf", pdf_file, "application/pdf")},
        )
    assert response.status_code == 201, response.text
    uploaded = response.json()

    try:
        yield uploaded
    finally:
        client.delete(f"/documents/{uploaded['id']}")


def test_process_document_creates_chunks() -> None:
    with patch(
        "app.services.document_processing.embed_texts",
        side_effect=lambda texts: _fake_embeddings(len(texts)),
    ):
        with TestClient(app) as client:
            with uploaded_sample_document(client) as uploaded:
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
    with patch(
        "app.services.document_processing.embed_texts",
        side_effect=lambda texts: _fake_embeddings(len(texts)),
    ):
        with TestClient(app) as client:
            with uploaded_sample_document(client) as uploaded:
                document_id = uploaded["id"]

                first = client.post(f"/documents/{document_id}/process")
                assert first.status_code == 200
                first_count = first.json()["chunk_count"]

                second = client.post(f"/documents/{document_id}/process")
                assert second.status_code == 400

                chunks_response = client.get(f"/documents/{document_id}/chunks")
                assert chunks_response.status_code == 200
                assert chunks_response.json()["total"] == first_count


def test_cancel_processing_marks_document_cancelled() -> None:
    with TestClient(app) as client:
        with uploaded_sample_document(client) as uploaded:
            document_id = uploaded["id"]
            from app.services.document_repository import update_document_status

            update_document_status(document_id, "processing")

            cancel_response = client.post(f"/documents/{document_id}/cancel")
            assert cancel_response.status_code == 200
            assert cancel_response.json()["status"] == "cancelled"


def test_processing_stops_when_cancelled() -> None:
    def cancel_before_embedding_update(texts: list[str]) -> list[list[float]]:
        from app.services.document_repository import update_document_status

        update_document_status(document_id, "cancelled")
        return _fake_embeddings(len(texts))

    with patch(
        "app.services.document_processing.embed_texts",
        side_effect=cancel_before_embedding_update,
    ):
        with TestClient(app) as client:
            with uploaded_sample_document(client) as uploaded:
                document_id = uploaded["id"]

                process_response = client.post(f"/documents/{document_id}/process")
                assert process_response.status_code == 409, process_response.text

                document_response = client.get(f"/documents/{document_id}")
                assert document_response.status_code == 200
                assert document_response.json()["status"] == "cancelled"

                chunks_response = client.get(f"/documents/{document_id}/chunks")
                assert chunks_response.status_code == 200
                assert chunks_response.json()["total"] == 0


def test_process_missing_document_returns_404() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/documents/00000000-0000-0000-0000-000000000099/process"
        )
    assert response.status_code == 404
