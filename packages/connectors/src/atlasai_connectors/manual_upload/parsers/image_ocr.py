"""OCR for standalone images and as a scanned-page fallback for PDFs
(pdf.py). Requires the system `tesseract` binary (installed in
apps/api/Dockerfile and apps/ai_atlas/Dockerfile)."""

from __future__ import annotations

import io

import pytesseract
from PIL import Image

from atlasai_connectors.manual_upload.chunking import chunk_text
from atlasai_connectors.manual_upload.parsers.base import ParsedChunk, ParsedDocument


def ocr_image(image: Image.Image) -> str:
    return str(pytesseract.image_to_string(image)).strip()


def parse_image(data: bytes) -> ParsedDocument:
    image = Image.open(io.BytesIO(data))
    text = ocr_image(image)
    chunks = [ParsedChunk(content=piece) for piece in chunk_text(text)]
    return ParsedDocument(full_text=text, chunks=chunks)
