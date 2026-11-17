"""Text chunking for document ingestion.

The chunker is deliberately simple and predictable: it splits on paragraph
boundaries first, then hard-splits any paragraph that is still too long,
carrying a configurable character overlap between consecutive chunks so a
fact that straddles a boundary stays retrievable from both sides.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_name: str
    index: int
    text: str


def split_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    """Split raw text into overlapping chunks of at most chunk_size chars."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    paragraphs = [p.strip() for p in text.split("\n\n")]
    units: list[str] = []
    for para in paragraphs:
        if not para:
            continue
        if len(para) <= chunk_size:
            units.append(para)
        else:
            units.extend(_hard_split(para, chunk_size, overlap))

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            combined = f"{tail}\n\n{unit}" if tail else unit
            current = combined if len(combined) <= chunk_size else unit
        else:
            current = unit
    if current:
        chunks.append(current)
    return chunks


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    step = chunk_size - overlap
    return [text[i : i + chunk_size] for i in range(0, len(text), step)]


def chunk_document(
    document_name: str,
    text: str,
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[Chunk]:
    parts = split_text(text, chunk_size=chunk_size, overlap=overlap)
    return [
        Chunk(
            chunk_id=f"{document_name}#chunk-{i + 1}",
            document_name=document_name,
            index=i + 1,
            text=part,
        )
        for i, part in enumerate(parts)
    ]
