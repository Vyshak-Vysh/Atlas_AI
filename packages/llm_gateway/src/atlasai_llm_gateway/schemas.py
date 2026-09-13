"""LLM-facing output schemas.

These are intentionally leaner than their atlasai_domain counterparts
(FindingDraft/FindingOutput, ContradictionEntry, TimelineEntry, CitationRef):
a JSON-schema-constrained model output requires every field with no default
to be present, so asking the model to fill in a full `CitationRef` — five
UUIDs, a location struct, timestamps — would force it to either fabricate
values it cannot actually know (source_version_id is never shown in the
prompt) or degrade citation quality by spending effort re-deriving data the
server already has. `CitationDraft` asks only for what the model can
actually get right (which chunk, and a supporting quote); grounded_answer.py
reconciles each one against the real evidence packet server-side before it
ever becomes a persisted CitationRef.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from atlasai_domain.contracts.findings import MissingEvidenceEntry
from atlasai_domain.enums import FindingStatus


class CitationDraft(BaseModel):
    evidence_chunk_id: UUID
    citation_label: str | None = None
    quote: str = Field(min_length=1)


class ContradictionDraft(BaseModel):
    side_a_summary: str = Field(min_length=1)
    side_a_citation: CitationDraft
    side_b_summary: str = Field(min_length=1)
    side_b_citation: CitationDraft
    why_it_matters: str = Field(min_length=1)


class TimelineEntryDraft(BaseModel):
    at: datetime
    label: str = Field(min_length=1)
    citation: CitationDraft | None = None


class FindingLLMOutput(BaseModel):
    """The exact schema passed as `output_format` to
    `client.messages.parse(...)`. No per-status required-field validation
    here — that runs once citations are reconciled into a real
    `atlasai_domain.contracts.findings.FindingDraft` (see
    grounded_answer.py), which is the object that actually enforces
    BD_v2.md §6."""

    status: FindingStatus
    summary: str = Field(min_length=1)
    facts: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    contradictions: list[ContradictionDraft] = Field(default_factory=list)
    missing_evidence: list[MissingEvidenceEntry] = Field(default_factory=list)
    timeline: list[TimelineEntryDraft] = Field(default_factory=list)
    citations: list[CitationDraft] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_next_step: str = Field(min_length=1)
    requires_human_review: bool = True
