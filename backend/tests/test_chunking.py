import pytest

from app.chunking import chunk_document, split_text


def test_split_respects_chunk_size():
    text = "\n\n".join(f"Paragraph {i} " + "word " * 40 for i in range(6))
    chunks = split_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)


def test_split_short_text_single_chunk():
    chunks = split_text("A short document body.", chunk_size=900, overlap=150)
    assert chunks == ["A short document body."]


def test_split_hard_splits_long_paragraph():
    chunks = split_text("x" * 1000, chunk_size=300, overlap=50)
    assert len(chunks) == 4  # step of 250 over 1000 chars
    assert all(len(chunk) <= 300 for chunk in chunks)


def test_split_rejects_bad_overlap():
    with pytest.raises(ValueError):
        split_text("text", chunk_size=100, overlap=100)


def test_chunk_document_ids_and_indexes():
    chunks = chunk_document("report.md", "Alpha text.\n\nBeta text.")
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "report.md#chunk-1"
    assert chunks[0].document_name == "report.md"
    assert chunks[0].index == 1
