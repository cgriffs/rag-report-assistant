"""Document ingestion: extract plain text from Markdown and PDF files."""

from __future__ import annotations

import io

from pypdf import PdfReader

SUPPORTED_SUFFIXES = (".md", ".markdown", ".txt", ".pdf")


def extract_text(filename: str, data: bytes) -> str:
    """Return the plain text of an uploaded document.

    Raises ValueError for unsupported file types or unreadable PDFs.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(data)
    if lower.endswith((".md", ".markdown", ".txt")):
        return data.decode("utf-8", errors="replace")
    raise ValueError(
        f"Unsupported file type for '{filename}'. "
        "Supported types: PDF, Markdown, plain text."
    )


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pypdf raises several exception types
        raise ValueError(f"Could not read PDF: {exc}") from exc
    return "\n\n".join(page.strip() for page in pages if page.strip())
