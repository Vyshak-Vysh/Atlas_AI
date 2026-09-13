"""PDF parsing: PyMuPDF (fitz) primary — native page numbers, handles
malformed PDFs, can render pages to images — with pypdf as a fallback if
PyMuPDF fails to open the file, and per-page OCR fallback (via
image_ocr.ocr_image) for pages whose extracted text is suspiciously short,
which usually means a scanned page with no text layer.
"""

from __future__ import annotations

import io

import fitz  # PyMuPDF
import pypdf
from PIL import Image

from atlasai_connectors.manual_upload.chunking import chunk_text
from atlasai_connectors.manual_upload.parsers.base import ParsedChunk, ParsedDocument, ParseError
from atlasai_connectors.manual_upload.parsers.image_ocr import ocr_image

_OCR_FALLBACK_MIN_CHARS = 20
_OCR_RENDER_ZOOM = 2.0  # ~144 DPI, a reasonable OCR-quality/speed tradeoff


def parse_pdf(data: bytes) -> ParsedDocument:
    try:
        return _parse_with_pymupdf(data)
    except Exception:  # noqa: BLE001 — PyMuPDF can raise several distinct exception types on malformed input
        return _parse_with_pypdf_fallback(data)


def _parse_with_pymupdf(data: bytes) -> ParsedDocument:
    chunks: list[ParsedChunk] = []
    full_text_parts: list[str] = []

    with fitz.open(stream=data, filetype="pdf") as doc:
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if len(text) < _OCR_FALLBACK_MIN_CHARS:
                text = _ocr_page(page) or text
            full_text_parts.append(text)
            for piece in chunk_text(text):
                chunks.append(ParsedChunk(content=piece, page_number=page_index))

    return ParsedDocument(full_text="\n\n".join(full_text_parts), chunks=chunks)


def _ocr_page(page: fitz.Page) -> str:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(_OCR_RENDER_ZOOM, _OCR_RENDER_ZOOM))
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    return ocr_image(image)


def _parse_with_pypdf_fallback(data: bytes) -> ParsedDocument:
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ParseError(f"could not parse PDF with either PyMuPDF or pypdf: {exc}") from exc

    chunks: list[ParsedChunk] = []
    full_text_parts: list[str] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        full_text_parts.append(text)
        for piece in chunk_text(text):
            chunks.append(ParsedChunk(content=piece, page_number=page_index))

    return ParsedDocument(full_text="\n\n".join(full_text_parts), chunks=chunks)
