"""Deterministic weighted reranking (TD_v2.md §7: "Rerank using relevance,
source authority, recency, exact phrase overlap, and requirement mapping").

A learned cross-encoder is explicitly deferred (see the implementation
plan) — this ships a transparent, debuggable scoring function first, and
the evaluation harness (packages/evaluation) gives a baseline to measure
any future reranker against before adopting one.
"""

from __future__ import annotations

from datetime import datetime

from atlasai_domain.contracts.evidence import EvidenceCandidate

_WEIGHT_LEXICAL = 0.35
_WEIGHT_VECTOR = 0.45
_WEIGHT_RECENCY = 0.10
_WEIGHT_PHRASE = 0.10


def _minmax_normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _best_timestamp(candidate: EvidenceCandidate) -> datetime | None:
    ts = candidate.timestamps
    return ts.effective_at or ts.modified_at or ts.authored_at or ts.imported_at


def _phrase_overlap_score(candidate_content: str, query_text: str) -> float:
    content_lower = candidate_content.lower()
    query_lower = query_text.strip().lower()
    if not query_lower:
        return 0.0
    if query_lower in content_lower:
        return 1.0
    query_words = {w for w in query_lower.split() if len(w) >= 4}
    if not query_words:
        return 0.0
    hits = sum(1 for w in query_words if w in content_lower)
    return hits / len(query_words)


def rerank(candidates: list[EvidenceCandidate], *, query_text: str, top_n: int = 10) -> list[EvidenceCandidate]:
    if not candidates:
        return []

    lexical_norm = _minmax_normalize([c.lexical_score or 0.0 for c in candidates])
    vector_norm = _minmax_normalize([c.vector_score or 0.0 for c in candidates])

    timestamps = [_best_timestamp(c) for c in candidates]
    epoch_values = [ts.timestamp() if ts is not None else 0.0 for ts in timestamps]
    recency_norm = _minmax_normalize(epoch_values)

    scored: list[tuple[float, EvidenceCandidate]] = []
    for i, candidate in enumerate(candidates):
        phrase_score = _phrase_overlap_score(candidate.content, query_text)
        combined = (
            _WEIGHT_LEXICAL * lexical_norm[i]
            + _WEIGHT_VECTOR * vector_norm[i]
            + _WEIGHT_RECENCY * recency_norm[i]
            + _WEIGHT_PHRASE * phrase_score
        )
        scored.append((combined, candidate.model_copy(update={"rerank_score": combined})))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [candidate for _, candidate in scored[:top_n]]
