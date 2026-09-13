"""Plain-text parsing: paragraph chunking, no location metadata beyond the
generic chunk_index the ingestion pipeline assigns."""

from __future__ import annotations

from atlasai_connectors.manual_upload.chunking import chunk_text
from atlasai_connectors.manual_upload.parsers.base import ParsedChunk, ParsedDocument


def parse_text(data: bytes) -> ParsedDocument:
    text = data.decode("utf-8", errors="replace")
    chunks = [ParsedChunk(content=piece) for piece in chunk_text(text)]
    return ParsedDocument(full_text=text, chunks=chunks)
