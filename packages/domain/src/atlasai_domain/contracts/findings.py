"""Finding output contract (BD_v1.md §8) and the per-status required-field
rules from BD_v2.md §6. `FindingOutput` is what packages/llm_gateway asks
the model to produce (via `client.messages.parse(..., output_format=
FindingOutput)`) and what apps/ai_atlas's FindingAssembler mechanically
re-validates before persisting — required fields are enforced by this
model's validator, not left to the model's discretion.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from atlasai_domain.contracts.evidence import CitationRef
from atlasai_domain.enums import FindingStatus


class ContradictionEntry(BaseModel):
    """One conflict between two evidence sides (BD_v2.md §6 CONFLICTING)."""

    side_a_summary: str = Field(min_length=1)
    side_a_citation: CitationRef
    side_b_summary: str = Field(min_length=1)
    side_b_citation: CitationRef
    why_it_matters: str = Field(min_length=1)


class TimelineEntry(BaseModel):
    at: datetime
    label: str = Field(min_length=1)
    citation: CitationRef | None = None


class MissingEvidenceEntry(BaseModel):
    """BD_v2.md §6 NOT_VERIFIED required output."""

    what_was_searched: str = Field(min_length=1)
    what_was_unavailable: str = Field(min_length=1)
    what_would_resolve_it: str = Field(min_length=1)


class FindingDraft(BaseModel):
    """Everything in the finding contract except `question`/`project_id` —
    what packages/llm_gateway actually asks the model to produce (via
    `client.messages.parse(..., output_format=FindingDraft)`). `question`
    and `project_id` are known to the caller already and are injected
    deterministically afterward (see FindingOutput.from_draft) rather than
    asked of the model, which would risk it mis-echoing a UUID it has no
    real way to get right. Per-status required-field enforcement
    (BD_v2.md §6) lives here so it applies the moment the model's raw
    output is parsed, before question/project_id are even attached."""

    status: FindingStatus
    summary: str = Field(min_length=1)
    facts: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    contradictions: list[ContradictionEntry] = Field(default_factory=list)
    missing_evidence: list[MissingEvidenceEntry] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    citations: list[CitationRef] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_next_step: str = Field(min_length=1)
    requires_human_review: bool = True

    @model_validator(mode="after")
    def _enforce_status_contract(self) -> FindingDraft:
        errors: list[str] = []

        def require_citations(min_count: int = 1) -> None:
            if len(self.citations) < min_count:
                errors.append(
                    f"status={self.status} requires at least {min_count} citation(s)"
                )

        def require_human_review() -> None:
            if not self.requires_human_review:
                errors.append(f"status={self.status} must set requires_human_review=true")

        match self.status:
            case FindingStatus.IN_SCOPE_SUPPORTED | FindingStatus.OUT_OF_SCOPE_SUPPORTED:
                require_citations(1)
            case FindingStatus.CONFLICTING:
                if len(self.contradictions) < 1:
                    errors.append("status=CONFLICTING requires at least one contradiction entry")
                require_human_review()
            case FindingStatus.AMBIGUOUS:
                require_human_review()
            case FindingStatus.NOT_VERIFIED:
                if len(self.missing_evidence) < 1:
                    errors.append("status=NOT_VERIFIED requires at least one missing_evidence entry")
            case FindingStatus.DELIVERED_VERIFIED | FindingStatus.PARTIAL:
                require_citations(1)
            case FindingStatus.SUPERSEDED:
                require_citations(1)
            case FindingStatus.PENDING_APPROVAL:
                require_human_review()

        if errors:
            raise ValueError("; ".join(errors))
        return self


class FindingOutput(FindingDraft):
    """The literal finding contract from BD_v1.md §8: a FindingDraft plus
    the caller-supplied question/project_id. Never constructed by asking
    the model for these two fields directly — see FindingDraft."""

    question: str = Field(min_length=1)
    project_id: UUID

    @classmethod
    def from_draft(cls, draft: FindingDraft, *, question: str, project_id: UUID) -> FindingOutput:
        return cls(question=question, project_id=project_id, **draft.model_dump())


class ClaimExtractionOutput(BaseModel):
    """ANALYZE step: statements extracted from one evidence chunk."""

    evidence_chunk_id: UUID
    claim_text: str = Field(min_length=1)
    claim_type: str
    polarity: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ConflictAnalysisOutput(BaseModel):
    """ANALYZE step: output of the analyze_conflict tool."""

    requirement_id: UUID | None = None
    has_conflict: bool
    contradictions: list[ContradictionEntry] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
