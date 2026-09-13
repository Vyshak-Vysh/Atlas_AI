"""Shared parser output shape. Every format-specific parser in this
package returns a `ParsedDocument` so the ingestion pipeline
(apps/ai_atlas/ingestion) never needs format-specific branching once
parsing is done.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedChunk:
    content: str
    page_number: int | None = None
    section_path: str | None = None
    sheet_name: str | None = None
    cell_range: str | None = None
    speaker: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    full_text: str
    chunks: list[ParsedChunk] = field(default_factory=list)


class UnsupportedFileTypeError(Exception):
    pass


class ParseError(Exception):
    pass
