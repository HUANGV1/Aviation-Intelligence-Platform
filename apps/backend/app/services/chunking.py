"""Text chunking service for extracted PDF pages.

Purpose: Splits page text into overlapping chunks sized for later embedding/RAG
using page-aware recursive splitting (paragraphs, lines, sentences, words).
Interactions: Consumes PageText from pdf_extraction.py; output is persisted by
chunk_repository.py. Uses word counts as a pragmatic token approximation.
"""

import re
from dataclasses import dataclass

from app.services.pdf_extraction import PageText

DEFAULT_CHUNK_WORDS = 800
DEFAULT_OVERLAP_WORDS = 120

# Split hierarchy: try larger semantic units first, then recurse to smaller ones.
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")
_LINE_SPLIT = re.compile(r"\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_HEADING_PATTERN = re.compile(
    r"^(?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9\s\-:,]{2,80}$"
)


@dataclass
class TextChunk:
    chunk_index: int
    text: str
    page_number: int | None
    section_title: str | None
    token_count: int


@dataclass(frozen=True)
class _SplitLevel:
    pattern: re.Pattern[str]
    joiner: str


_SPLIT_LEVELS: tuple[_SplitLevel, ...] = (
    _SplitLevel(_PARAGRAPH_SPLIT, "\n\n"),
    _SplitLevel(_LINE_SPLIT, "\n"),
    _SplitLevel(_SENTENCE_SPLIT, " "),
)


def _word_count(text: str) -> int:
    return len(text.split())


def _detect_section_title(text: str) -> str | None:
    """Return the first heading-like line on a page, if any."""
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate or _word_count(candidate) > 12:
            continue
        if candidate.endswith("."):
            continue
        if _HEADING_PATTERN.match(candidate):
            return candidate
    return None


def _split_at_level(text: str, level: _SplitLevel) -> list[str]:
    parts = [part.strip() for part in level.pattern.split(text) if part.strip()]
    return parts if parts else ([text.strip()] if text.strip() else [])


def _hard_split_words(text: str, *, chunk_words: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    segments: list[str] = []
    for start in range(0, len(words), chunk_words):
        segment = " ".join(words[start : start + chunk_words])
        if segment:
            segments.append(segment)
    return segments


def _recursive_split_text(
    text: str,
    *,
    chunk_words: int,
    level_index: int = 0,
) -> list[str]:
    normalized = " ".join(text.split()) if level_index >= len(_SPLIT_LEVELS) else text.strip()
    if not normalized:
        return []

    if _word_count(normalized) <= chunk_words:
        return [normalized.strip()]

    if level_index >= len(_SPLIT_LEVELS):
        return _hard_split_words(normalized, chunk_words=chunk_words)

    level = _SPLIT_LEVELS[level_index]
    parts = _split_at_level(normalized, level)

    if len(parts) == 1:
        return _recursive_split_text(
            normalized,
            chunk_words=chunk_words,
            level_index=level_index + 1,
        )

    merged: list[str] = []
    buffer: list[str] = []
    buffer_words = 0

    def flush_buffer() -> None:
        nonlocal buffer, buffer_words
        if buffer:
            merged.append(level.joiner.join(buffer))
            buffer = []
            buffer_words = 0

    for part in parts:
        part_words = _word_count(part)

        if part_words > chunk_words:
            flush_buffer()
            merged.extend(
                _recursive_split_text(
                    part,
                    chunk_words=chunk_words,
                    level_index=level_index + 1,
                )
            )
            continue

        if buffer_words + part_words <= chunk_words:
            buffer.append(part)
            buffer_words += part_words
        else:
            flush_buffer()
            buffer = [part]
            buffer_words = part_words

    flush_buffer()
    return merged


def _apply_overlap(segments: list[str], *, overlap_words: int) -> list[str]:
    if overlap_words <= 0 or len(segments) <= 1:
        return segments

    overlapped: list[str] = [segments[0]]
    for index in range(1, len(segments)):
        previous_words = segments[index - 1].split()
        overlap = previous_words[-overlap_words:]
        current_words = segments[index].split()
        combined = overlap + current_words
        overlapped.append(" ".join(combined))

    return overlapped


def _chunk_page_text(
    page: PageText,
    *,
    chunk_words: int,
    overlap_words: int,
    start_index: int,
    section_title: str | None,
) -> tuple[list[TextChunk], int]:
    if not page.text.strip():
        return [], start_index

    segments = _recursive_split_text(page.text, chunk_words=chunk_words)
    segments = _apply_overlap(segments, overlap_words=overlap_words)

    chunks: list[TextChunk] = []
    index = start_index

    for segment in segments:
        chunks.append(
            TextChunk(
                chunk_index=index,
                text=segment,
                page_number=page.page_number,
                section_title=section_title,
                token_count=_word_count(segment),
            )
        )
        index += 1

    return chunks, index


def chunk_pages(
    pages: list[PageText],
    *,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[TextChunk]:
    all_chunks: list[TextChunk] = []
    next_index = 0

    for page in pages:
        section_title = _detect_section_title(page.text)
        page_chunks, next_index = _chunk_page_text(
            page,
            chunk_words=chunk_words,
            overlap_words=overlap_words,
            start_index=next_index,
            section_title=section_title,
        )
        all_chunks.extend(page_chunks)

    return all_chunks
