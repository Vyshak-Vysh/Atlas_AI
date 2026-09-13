"""Evaluation fixture schema. TD_v2.md §9 requires the evaluation dataset
to cover: in-scope, out-of-scope, conflicting, ambiguous, not-verified,
superseded, partially-delivered, prompt-injection attempts, and permission
boundary cases — EvalCategory is exactly that list.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from atlasai_domain.enums import FindingStatus


class EvalCategory(StrEnum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    CONFLICTING = "CONFLICTING"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_VERIFIED = "NOT_VERIFIED"
    SUPERSEDED = "SUPERSEDED"
    PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    PERMISSION_BOUNDARY = "PERMISSION_BOUNDARY"


class EvalEvidenceFixture(BaseModel):
    """One piece of evidence to seed before asking the eval question —
    ingested through the real manual-upload pipeline, not inserted
    directly into evidence_chunks, so the eval exercises the same parse/
    chunk/embed path production traffic does."""

    filename: str
    mime_type: str
    text_content: str
    """Fixture evidence is authored as plain text and uploaded as a
    text/plain file — sufficient to exercise retrieval/analysis without
    needing binary PDF/DOCX fixtures checked into the repo."""


class EvalCase(BaseModel):
    id: str
    category: EvalCategory
    description: str = Field(min_length=1)
    evidence: list[EvalEvidenceFixture] = Field(default_factory=list)
    question: str = Field(min_length=1)
    expected_status: FindingStatus | None = None
    """None for PERMISSION_BOUNDARY cases, which assert a 404 denial
    rather than a finding status."""
    expect_requires_human_review: bool | None = None
    notes: str | None = None
