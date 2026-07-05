"""Unit tests for page-aware recursive text chunking."""

from app.services.chunking import (
    DEFAULT_CHUNK_WORDS,
    DEFAULT_OVERLAP_WORDS,
    TextChunk,
    chunk_pages,
)
from app.services.pdf_extraction import PageText


def test_chunk_pages_preserves_page_number() -> None:
    words = ["word"] * 1000
    pages = [PageText(page_number=1, text=" ".join(words))]

    chunks = chunk_pages(pages, chunk_words=800, overlap_words=120)

    assert len(chunks) >= 2
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_chunk_pages_empty_input() -> None:
    assert chunk_pages([]) == []


def test_chunk_pages_splits_on_paragraph_boundaries() -> None:
    paragraph_a = " ".join(["alpha"] * 500)
    paragraph_b = " ".join(["beta"] * 500)
    text = f"{paragraph_a}\n\n{paragraph_b}"
    pages = [PageText(page_number=2, text=text)]

    chunks = chunk_pages(pages, chunk_words=800, overlap_words=0)

    assert len(chunks) == 2
    assert all(chunk.page_number == 2 for chunk in chunks)
    assert "alpha" in chunks[0].text
    assert "beta" in chunks[1].text


def test_chunk_pages_splits_on_sentence_boundaries() -> None:
    sentences = [f"Sentence number {index} has several words here." for index in range(120)]
    text = " ".join(sentences)
    pages = [PageText(page_number=3, text=text)]

    chunks = chunk_pages(pages, chunk_words=200, overlap_words=0)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.text.endswith(".")
        assert chunk.page_number == 3


def test_chunk_pages_applies_overlap() -> None:
    words = ["token"] * 1000
    pages = [PageText(page_number=4, text=" ".join(words))]

    chunks = chunk_pages(pages, chunk_words=800, overlap_words=120)

    assert len(chunks) >= 2
    first_tail = chunks[0].text.split()[-120:]
    second_head = chunks[1].text.split()[:120]
    assert first_tail == second_head


def test_chunk_pages_long_unbroken_text_falls_back_to_word_split() -> None:
    text = " ".join(["run"] * 900)
    pages = [PageText(page_number=5, text=text)]

    chunks = chunk_pages(pages, chunk_words=400, overlap_words=0)

    assert len(chunks) >= 2
    assert all(chunk.page_number == 5 for chunk in chunks)
    assert sum(chunk.token_count for chunk in chunks) >= 900


def test_chunk_pages_detects_section_title() -> None:
    body = " ".join(["content"] * 50)
    text = f"1 Introduction\n\n{body}"
    pages = [PageText(page_number=6, text=text)]

    chunks = chunk_pages(pages, chunk_words=800, overlap_words=0)

    assert len(chunks) >= 1
    assert chunks[0].section_title == "1 Introduction"


def test_text_chunk_contract_unchanged() -> None:
    chunk = TextChunk(
        chunk_index=0,
        text="sample",
        page_number=1,
        section_title=None,
        token_count=1,
    )
    assert chunk.chunk_index == 0
    assert chunk.page_number == 1


def test_chunk_pages_default_parameters() -> None:
    short_page = PageText(page_number=1, text="Short aviation briefing.")
    chunks = chunk_pages([short_page])

    assert len(chunks) == 1
    assert chunks[0].token_count <= DEFAULT_CHUNK_WORDS
    assert DEFAULT_OVERLAP_WORDS == 120
