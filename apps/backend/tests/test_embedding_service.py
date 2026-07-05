"""Unit tests for embedding text formatting and batch behavior."""

from unittest.mock import MagicMock, patch

import pytest

from app.services import embedding_service
from app.services.embedding_service import (
    EmbeddingError,
    embed_query,
    embed_texts,
    format_document_text,
    format_query_text,
)


def test_format_document_text_uses_title() -> None:
    formatted = format_document_text(text="Runway incursion guidance.", title="Section 3")
    assert formatted == "title: Section 3 | text: Runway incursion guidance."


def test_format_document_text_defaults_missing_title() -> None:
    formatted = format_document_text(text="Weather minimums apply.", title=None)
    assert formatted == "title: none | text: Weather minimums apply."


def test_format_query_text_uses_search_task() -> None:
    formatted = format_query_text("What are the contributing factors?")
    assert formatted == "task: search result | query: What are the contributing factors?"


def test_format_query_text_rejects_empty_query() -> None:
    with pytest.raises(EmbeddingError):
        format_query_text("   ")


def test_embedding_batches_respect_token_budget() -> None:
    texts = [
        "alpha " * 200,
        "bravo " * 200,
        "charlie " * 200,
    ]

    with (
        patch.object(embedding_service.settings, "embedding_batch_size", 10),
        patch.object(embedding_service.settings, "embedding_request_token_budget", 900),
    ):
        batches = embedding_service._iter_token_limited_batches(texts)

    assert len(batches) == 2
    assert batches[0] == texts[:2]
    assert batches[1] == texts[2:]


@patch("app.services.embedding_service._get_client")
def test_embed_texts_returns_one_embedding_per_input(mock_get_client: MagicMock) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    first = MagicMock()
    first.values = [0.1] * 768
    second = MagicMock()
    second.values = [0.2] * 768

    mock_result = MagicMock()
    mock_result.embeddings = [first, second]
    mock_client.models.embed_content.return_value = mock_result

    with (
        patch.object(embedding_service.settings, "embedding_dimensions", 768),
        patch.object(embedding_service.settings, "embedding_tokens_per_minute", 0),
    ):
        embeddings = embed_texts(["chunk one", "chunk two"])

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768
    assert len(embeddings[1]) == 768
    mock_client.models.embed_content.assert_called_once()


@patch("app.services.embedding_service.embed_text")
def test_embed_query_formats_search_prompt(mock_embed_text: MagicMock) -> None:
    mock_embed_text.return_value = [0.0] * 768

    embed_query("visibility requirements")

    mock_embed_text.assert_called_once_with(
        "task: search result | query: visibility requirements"
    )
