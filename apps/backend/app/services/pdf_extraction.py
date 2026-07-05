"""PDF text extraction service.

Purpose: Extracts page-level text from stored PDF files using pypdf and pdfplumber.
Interactions: Called by document processing flow. Uses resolve_document_path()
from document_storage.py to safely locate uploaded PDFs.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be parsed or has no extractable text."""


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class ExtractionResult:
    page_count: int
    pages: list[PageText]


def _normalize_text(raw_text: str) -> str:
    return " ".join((raw_text or "").split())


def _extract_with_pypdf(file_path: Path) -> ExtractionResult:
    reader = PdfReader(str(file_path), strict=False)
    page_count = len(reader.pages)
    pages: list[PageText] = []

    for index, page in enumerate(reader.pages, start=1):
        normalized = _normalize_text(page.extract_text() or "")
        if normalized:
            pages.append(PageText(page_number=index, text=normalized))

    return ExtractionResult(page_count=page_count, pages=pages)


def _extract_with_pdfplumber(file_path: Path) -> ExtractionResult:
    pages: list[PageText] = []

    with pdfplumber.open(str(file_path)) as pdf:
        page_count = len(pdf.pages)
        for index, page in enumerate(pdf.pages, start=1):
            normalized = _normalize_text(page.extract_text() or "")
            if normalized:
                pages.append(PageText(page_number=index, text=normalized))

    return ExtractionResult(page_count=page_count, pages=pages)


def extract_pdf_text(file_path: Path) -> ExtractionResult:
    parse_errors: list[str] = []
    best_result: ExtractionResult | None = None

    for name, extractor in (
        ("pypdf", _extract_with_pypdf),
        ("pdfplumber", _extract_with_pdfplumber),
    ):
        try:
            result = extractor(file_path)
            if best_result is None or result.page_count > best_result.page_count:
                best_result = result
            if result.pages:
                logger.info(
                    "Extracted text from %s using %s (%s pages, %s text pages)",
                    file_path.name,
                    name,
                    result.page_count,
                    len(result.pages),
                )
                return result
        except PdfReadError as exc:
            parse_errors.append(f"{name}: {exc}")
            logger.warning("PDF parse warning from %s: %s", name, exc)
        except Exception as exc:
            parse_errors.append(f"{name}: {exc}")
            logger.warning("PDF extraction failed with %s: %s", name, exc)

    if best_result and best_result.page_count > 0:
        raise PdfExtractionError(
            "No extractable text found in this PDF. It may be scanned or image-only; "
            "OCR is not supported in the MVP."
        )

    if parse_errors:
        raise PdfExtractionError(
            "Could not parse this PDF file. Try re-saving or exporting it as a standard PDF."
        )

    raise PdfExtractionError("No extractable text found in PDF.")
