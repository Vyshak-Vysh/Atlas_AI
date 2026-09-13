"""Unit tests for the manual-upload parsers' shared chunking helper."""

from __future__ import annotations

from atlasai_connectors.manual_upload.chunking import chunk_text


def test_short_text_becomes_one_chunk() -> None:
    chunks = chunk_text("This is a short scope statement.\n\nIt fits in one chunk.")
    assert len(chunks) == 1
    assert "short scope statement" in chunks[0]


def test_empty_text_produces_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_long_text_is_split_into_multiple_chunks() -> None:
    paragraph = "Feature X is included in phase 1 per the statement of work. " * 40
    text = "\n\n".join([paragraph] * 5)
    chunks = chunk_text(text, max_chars=500, overlap_chars=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 + 50 for c in chunks)  # overlap can push slightly over max_chars


def test_a_single_paragraph_longer_than_max_chars_is_hard_split() -> None:
    huge_paragraph = "word " * 2000  # ~10000 chars, no paragraph breaks
    chunks = chunk_text(huge_paragraph, max_chars=1000, overlap_chars=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1000
