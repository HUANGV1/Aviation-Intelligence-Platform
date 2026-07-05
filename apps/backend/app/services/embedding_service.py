"""Gemini embedding service for document chunks and search queries.

Purpose: Generates vector embeddings via the Gemini API for pgvector storage
and semantic search. Interactions: Called by document_processing.py during
processing and search_service.py during retrieval.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Literal

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

SearchTask = Literal["search result", "question answering"]

_client: genai.Client | None = None
_token_window: deque[tuple[float, int]] = deque()


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise EmbeddingError(
                "GEMINI_API_KEY is required for embeddings. Set it in apps/backend/.env."
            )
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def format_document_text(*, text: str, title: str | None) -> str:
    document_title = title.strip() if title and title.strip() else "none"
    return f"title: {document_title} | text: {text}"


def format_query_text(query: str, *, task: SearchTask = "search result") -> str:
    normalized = query.strip()
    if not normalized:
        raise EmbeddingError("Query text must not be empty.")
    return f"task: {task} | query: {normalized}"


def _validate_embedding(values: list[float]) -> list[float]:
    expected = settings.embedding_dimensions
    if len(values) != expected:
        raise EmbeddingError(
            f"Expected embedding dimension {expected}, got {len(values)}."
        )
    return values


def _extract_embedding_values(result: types.EmbedContentResponse) -> list[list[float]]:
    if not result.embeddings:
        raise EmbeddingError("Gemini returned no embeddings.")

    values_list: list[list[float]] = []
    for embedding in result.embeddings:
        if embedding.values is None:
            raise EmbeddingError("Gemini returned an embedding without values.")
        values_list.append(_validate_embedding(list(embedding.values)))

    return values_list


def _estimate_input_tokens(text: str) -> int:
    """Estimate Gemini input tokens conservatively without a tokenizer dependency."""
    if not text:
        return 1
    char_estimate = (len(text) + 2) // 3
    word_estimate = int(len(text.split()) * 1.4)
    return max(1, char_estimate, word_estimate)


def _iter_token_limited_batches(texts: list[str]) -> list[list[str]]:
    max_items = max(1, settings.embedding_batch_size)
    token_budget = max(1, settings.embedding_request_token_budget)

    batches: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0

    for text in texts:
        estimated_tokens = _estimate_input_tokens(text)

        if current and (
            len(current) >= max_items
            or current_tokens + estimated_tokens > token_budget
        ):
            batches.append(current)
            current = []
            current_tokens = 0

        current.append(text)
        current_tokens += estimated_tokens

    if current:
        batches.append(current)

    return batches


def _wait_for_token_capacity(estimated_tokens: int) -> None:
    tokens_per_minute = settings.embedding_tokens_per_minute
    if tokens_per_minute <= 0:
        return

    now = time.monotonic()
    while _token_window and now - _token_window[0][0] >= 60:
        _token_window.popleft()

    used_tokens = sum(tokens for _, tokens in _token_window)
    if used_tokens + estimated_tokens <= tokens_per_minute:
        _token_window.append((now, estimated_tokens))
        return

    oldest_time, _ = _token_window[0]
    sleep_seconds = max(0.0, 60 - (now - oldest_time))
    logger.info(
        "Waiting %.1f seconds for Gemini embedding token quota capacity.",
        sleep_seconds,
    )
    time.sleep(sleep_seconds)

    now = time.monotonic()
    while _token_window and now - _token_window[0][0] >= 60:
        _token_window.popleft()
    _token_window.append((now, estimated_tokens))


def embed_text(text: str) -> list[float]:
    embeddings = embed_texts([text])
    return embeddings[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = _get_client()
    all_embeddings: list[list[float]] = []

    for batch in _iter_token_limited_batches(texts):
        estimated_tokens = sum(_estimate_input_tokens(item) for item in batch)
        _wait_for_token_capacity(estimated_tokens)
        contents = [
            types.Content(parts=[types.Part.from_text(text=item)])
            for item in batch
        ]

        try:
            result = client.models.embed_content(
                model=settings.embedding_model,
                contents=contents,
                config=types.EmbedContentConfig(
                    output_dimensionality=settings.embedding_dimensions
                ),
            )
        except Exception as exc:
            logger.exception("Gemini embedding request failed.")
            raise EmbeddingError("Failed to generate embeddings.") from exc

        batch_embeddings = _extract_embedding_values(result)
        if len(batch_embeddings) != len(batch):
            raise EmbeddingError(
                "Gemini returned a different number of embeddings than requested."
            )
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def embed_query(query: str, *, task: SearchTask = "search result") -> list[float]:
    return embed_text(format_query_text(query, task=task))
