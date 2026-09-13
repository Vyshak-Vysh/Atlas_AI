"""Shared text-chunking helper used by parsers that emit long blocks of
text per natural unit (a PDF page, a DOCX section). Splits on paragraph
boundaries with a small overlap so a claim split across two paragraphs
still has surrounding context in at least one chunk — this is a
character-budget heuristic (~1500 chars comfortably fits under
bge-base-en-v1.5's ~512-token limit for typical English text), not a real
tokenizer, since pulling in a full tokenizer just to size chunks isn't
worth the dependency for this build.
"""

from __future__ import annotations

_MAX_CHARS = 1500
_OVERLAP_CHARS = 150


def chunk_text(text: str, *, max_chars: int = _MAX_CHARS, overlap_chars: int = _OVERLAP_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = f"{tail}\n\n{paragraph}" if tail else paragraph
        else:
            # A single paragraph longer than max_chars — hard-split it.
            for start in range(0, len(paragraph), max_chars - overlap_chars):
                chunks.append(paragraph[start : start + max_chars])
            current = ""
    if current:
        chunks.append(current)
    return chunks
