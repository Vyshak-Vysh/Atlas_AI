"""Format dispatch: one parser per supported MIME type, all returning the
shared ParsedDocument shape (base.py)."""

from __future__ import annotations

from collections.abc import Callable

from atlasai_connectors.manual_upload.parsers.base import ParsedDocument, UnsupportedFileTypeError
from atlasai_connectors.manual_upload.parsers.docx import parse_docx
from atlasai_connectors.manual_upload.parsers.image_ocr import parse_image
from atlasai_connectors.manual_upload.parsers.pdf import parse_pdf
from atlasai_connectors.manual_upload.parsers.text import parse_text
from atlasai_connectors.manual_upload.parsers.xlsx import parse_xlsx

_PARSERS: dict[str, Callable[[bytes], ParsedDocument]] = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": parse_xlsx,
    "text/plain": parse_text,
    "text/markdown": parse_text,
    "text/csv": parse_text,
    "image/png": parse_image,
    "image/jpeg": parse_image,
    "image/tiff": parse_image,
}

SUPPORTED_MIME_TYPES = frozenset(_PARSERS)


def parse_document(data: bytes, mime_type: str) -> ParsedDocument:
    parser = _PARSERS.get(mime_type)
    if parser is None:
        raise UnsupportedFileTypeError(f"unsupported MIME type: {mime_type}")
    return parser(data)


__all__ = ["SUPPORTED_MIME_TYPES", "ParsedDocument", "UnsupportedFileTypeError", "parse_document"]
