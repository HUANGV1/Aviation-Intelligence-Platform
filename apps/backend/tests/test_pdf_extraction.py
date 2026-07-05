"""Unit tests for PDF extraction error handling."""

from pathlib import Path

import pytest

from app.services.pdf_extraction import PdfExtractionError, extract_pdf_text

SAMPLE_TEXT_PDF = (
    Path(__file__).resolve().parents[3] / "sample-data" / "test-process.pdf"
)
SAMPLE_BLANK_PDF = (
    Path(__file__).resolve().parents[3] / "sample-data" / "test-upload.pdf"
)


def test_extract_text_pdf_succeeds() -> None:
    result = extract_pdf_text(SAMPLE_TEXT_PDF)
    assert result.page_count >= 1
    assert len(result.pages) >= 1


def test_extract_blank_pdf_raises_clear_error() -> None:
    with pytest.raises(PdfExtractionError, match="No extractable text"):
        extract_pdf_text(SAMPLE_BLANK_PDF)
