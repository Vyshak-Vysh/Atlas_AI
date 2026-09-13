"""Unit tests for BD_v2.md §6's per-status required-field contract, enforced
by FindingDraft's validator (packages/domain/contracts/findings.py)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from atlasai_domain.contracts.evidence import CitationRef
from atlasai_domain.contracts.findings import ContradictionEntry, FindingDraft, MissingEvidenceEntry
from atlasai_domain.enums import FindingStatus


def _citation() -> CitationRef:
    return CitationRef(
        evidence_chunk_id=uuid.uuid4(),
        source_record_id=uuid.uuid4(),
        source_version_id=uuid.uuid4(),
        quote="the scope document says feature X is in phase 1",
    )


def _base_kwargs() -> dict:
    return {
        "summary": "Feature X is in scope for phase 1.",
        "confidence": 0.9,
        "recommended_next_step": "Confirm with the client.",
    }


def test_in_scope_supported_requires_a_citation() -> None:
    with pytest.raises(ValidationError, match="requires at least 1 citation"):
        FindingDraft(status=FindingStatus.IN_SCOPE_SUPPORTED, citations=[], **_base_kwargs())

    # Should succeed with a citation attached.
    FindingDraft(status=FindingStatus.IN_SCOPE_SUPPORTED, citations=[_citation()], **_base_kwargs())


def test_conflicting_requires_a_contradiction_and_human_review() -> None:
    with pytest.raises(ValidationError, match="requires at least one contradiction"):
        FindingDraft(status=FindingStatus.CONFLICTING, contradictions=[], **_base_kwargs())

    contradiction = ContradictionEntry(
        side_a_summary="Client says X is included.",
        side_a_citation=_citation(),
        side_b_summary="SOW excludes X from phase 1.",
        side_b_citation=_citation(),
        why_it_matters="Affects billing for phase 1.",
    )
    finding = FindingDraft(
        status=FindingStatus.CONFLICTING, contradictions=[contradiction], requires_human_review=True, **_base_kwargs()
    )
    assert finding.requires_human_review is True

    with pytest.raises(ValidationError, match="requires_human_review"):
        FindingDraft(
            status=FindingStatus.CONFLICTING,
            contradictions=[contradiction],
            requires_human_review=False,
            **_base_kwargs(),
        )


def test_not_verified_requires_missing_evidence_entry() -> None:
    with pytest.raises(ValidationError, match="requires at least one missing_evidence"):
        FindingDraft(status=FindingStatus.NOT_VERIFIED, missing_evidence=[], **_base_kwargs())

    entry = MissingEvidenceEntry(
        what_was_searched="scope documents and emails",
        what_was_unavailable="no meeting notes for the kickoff call",
        what_would_resolve_it="the kickoff meeting recording or minutes",
    )
    finding = FindingDraft(status=FindingStatus.NOT_VERIFIED, missing_evidence=[entry], **_base_kwargs())
    assert finding.status == FindingStatus.NOT_VERIFIED


def test_ambiguous_requires_human_review() -> None:
    with pytest.raises(ValidationError, match="requires_human_review"):
        FindingDraft(status=FindingStatus.AMBIGUOUS, requires_human_review=False, **_base_kwargs())


def test_confidence_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        FindingDraft(status=FindingStatus.NOT_VERIFIED, confidence=1.5, missing_evidence=[
            MissingEvidenceEntry(what_was_searched="x", what_was_unavailable="y", what_would_resolve_it="z")
        ], summary="s", recommended_next_step="n")


def test_timeline_entry_at_is_a_real_datetime() -> None:
    from atlasai_domain.contracts.findings import TimelineEntry

    entry = TimelineEntry(at=datetime.now(UTC), label="Kickoff meeting")
    assert entry.citation is None
