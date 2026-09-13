"""Evidence candidate and citation contracts.

These mirror `evidence_chunks` / `finding_citations` column shapes (see
docs/ERD_FINAL.md) but are transport-agnostic Pydantic models — packages/db
maps ORM rows to these, packages/retrieval and the agent steps only ever
see these types.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceLocation(BaseModel):
    """Where inside a source a chunk of evidence physically lives.

    Every field is optional because location shape differs by source type:
    a PDF has page_number/section_path, a spreadsheet has sheet_name/
    cell_range, a transcript has speaker/start_ms/end_ms.
    """

    page_number: int | None = None
    section_path: str | None = None
    sheet_name: str | None = None
    cell_range: str | None = None
    speaker: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None


class EvidenceTimestamps(BaseModel):
    """The five distinct timestamps every evidence-bearing object must carry
    (ATLASAI_MASTER_SPEC.md §5 / TD_v2.md §6)."""

    authored_at: datetime | None = None
    modified_at: datetime | None = None
    imported_at: datetime | None = None
    meeting_at: datetime | None = None
    effective_at: datetime | None = None


class CitationRef(BaseModel):
    """A single citation pointing at one evidence chunk."""

    evidence_chunk_id: UUID
    source_record_id: UUID
    source_version_id: UUID
    citation_label: str | None = None
    quote: str = Field(min_length=1)
    location: EvidenceLocation = Field(default_factory=EvidenceLocation)
    timestamps: EvidenceTimestamps = Field(default_factory=EvidenceTimestamps)
    source_url: str | None = None


class EvidenceCandidate(BaseModel):
    """One hybrid-retrieval result, before or after reranking."""

    evidence_chunk_id: UUID
    source_record_id: UUID
    source_version_id: UUID
    content: str
    lexical_score: float | None = None
    vector_score: float | None = None
    rerank_score: float | None = None
    location: EvidenceLocation = Field(default_factory=EvidenceLocation)
    timestamps: EvidenceTimestamps = Field(default_factory=EvidenceTimestamps)
    requirement_ids: list[UUID] = Field(default_factory=list)
    visibility: str = "PROJECT"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_citation(self, *, citation_label: str | None = None, quote: str | None = None) -> CitationRef:
        return CitationRef(
            evidence_chunk_id=self.evidence_chunk_id,
            source_record_id=self.source_record_id,
            source_version_id=self.source_version_id,
            citation_label=citation_label,
            quote=quote or self.content[:500],
            location=self.location,
            timestamps=self.timestamps,
        )
