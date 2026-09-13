"""XLSX parsing via openpyxl. Each chunk is a block of rows from one sheet,
rendered as pipe-delimited text with an explicit cell_range (e.g.
"A1:D25") so a citation can point at exactly which cells it came from.
"""

from __future__ import annotations

import io

import openpyxl
from openpyxl.utils import get_column_letter

from atlasai_connectors.manual_upload.parsers.base import ParsedChunk, ParsedDocument

_ROWS_PER_CHUNK = 25


def parse_xlsx(data: bytes) -> ParsedDocument:
    workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)

    chunks: list[ParsedChunk] = []
    full_text_parts: list[str] = []

    for sheet in workbook.worksheets:
        rows = [row for row in sheet.iter_rows(values_only=True) if any(cell is not None for cell in row)]
        if not rows:
            continue
        max_col = max(len(row) for row in rows)

        for start in range(0, len(rows), _ROWS_PER_CHUNK):
            block = rows[start : start + _ROWS_PER_CHUNK]
            lines = ["\t".join("" if cell is None else str(cell) for cell in row) for row in block]
            content = f"[{sheet.title}]\n" + "\n".join(lines)
            cell_range = f"A{start + 1}:{get_column_letter(max_col)}{start + len(block)}"
            chunks.append(ParsedChunk(content=content, sheet_name=sheet.title, cell_range=cell_range))
            full_text_parts.append(content)

    return ParsedDocument(full_text="\n\n".join(full_text_parts), chunks=chunks)
