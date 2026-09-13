"""Unit tests for the deterministic weighted reranker (TD_v2.md §7)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from atlasai_domain.contracts.evidence import EvidenceCandidate, EvidenceTimestamps
from atlasai_retrieval.rerank import rerank

_FIXED_NOW = datetime.now(UTC)


def _candidate(
    content: str, *, lexical_score: float | None, vector_score: float | None, days_old: int = 0
) -> EvidenceCandidate:
    return EvidenceCandidate(
        evidence_chunk_id=uuid.uuid4(),
        source_record_id=uuid.uuid4(),
        source_version_id=uuid.uuid4(),
        content=content,
        lexical_score=lexical_score,
        vector_score=vector_score,
        # A fixed reference time (not datetime.now() per call) so tests that
        # hold days_old constant across candidates get a genuine recency tie
        # instead of an accidental few-microsecond difference from
        # construction order.
        timestamps=EvidenceTimestamps(effective_at=_FIXED_NOW - timedelta(days=days_old)),
    )


def test_higher_combined_scores_rank_first() -> None:
    strong = _candidate("feature X is in phase 1 scope", lexical_score=0.9, vector_score=0.9)
    weak = _candidate("unrelated meeting notes about lunch", lexical_score=0.1, vector_score=0.1)
    ranked = rerank([weak, strong], query_text="is feature X in phase 1?", top_n=10)
    assert ranked[0].evidence_chunk_id == strong.evidence_chunk_id


def test_exact_phrase_overlap_boosts_ranking() -> None:
    exact = _candidate("Is feature X in phase 1?", lexical_score=0.5, vector_score=0.5)
    generic = _candidate("Some other scope statement entirely", lexical_score=0.5, vector_score=0.5)
    ranked = rerank([generic, exact], query_text="Is feature X in phase 1?", top_n=10)
    assert ranked[0].evidence_chunk_id == exact.evidence_chunk_id


def test_more_recent_evidence_is_favored_when_other_scores_tie() -> None:
    recent = _candidate("scope note", lexical_score=0.5, vector_score=0.5, days_old=1)
    old = _candidate("scope note", lexical_score=0.5, vector_score=0.5, days_old=400)
    ranked = rerank([old, recent], query_text="unrelated query text", top_n=10)
    assert ranked[0].evidence_chunk_id == recent.evidence_chunk_id


def test_top_n_limits_result_count() -> None:
    candidates = [_candidate(f"chunk {i}", lexical_score=float(i), vector_score=float(i)) for i in range(20)]
    ranked = rerank(candidates, query_text="chunk", top_n=5)
    assert len(ranked) == 5


def test_empty_candidates_returns_empty_list() -> None:
    assert rerank([], query_text="anything", top_n=10) == []
