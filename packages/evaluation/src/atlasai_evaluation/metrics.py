"""Evaluation metrics (BD_v1.md §10 business metrics): Retrieval Recall@K,
evidence citation coverage, unsupported-assertion rate, and conflict-
detection precision. Pure functions over already-collected results, so
they're unit-testable without a live LLM or database.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from pydantic import BaseModel

from atlasai_domain.enums import FindingStatus
from atlasai_evaluation.schema import EvalCase, EvalCategory


class EvalCaseResult(BaseModel):
    case_id: str
    category: EvalCategory
    passed: bool
    actual_status: FindingStatus | None = None
    actual_requires_human_review: bool | None = None
    citation_count: int = 0
    fact_count: int = 0
    detail: str | None = None


def recall_at_k(retrieved_ids: Sequence[uuid.UUID], relevant_ids: set[uuid.UUID]) -> float:
    """What fraction of the known-relevant evidence chunks were present in
    the retrieved set (already truncated to top-K by the caller)."""
    if not relevant_ids:
        return 1.0
    found = sum(1 for rid in retrieved_ids if rid in relevant_ids)
    return found / len(relevant_ids)


def citation_coverage(results: Sequence[EvalCaseResult]) -> float:
    """Of cases whose expected status requires at least one citation
    (BD_v2.md §6), what fraction actually got one."""
    requiring_citation = [
        r
        for r in results
        if r.actual_status
        in {
            FindingStatus.IN_SCOPE_SUPPORTED,
            FindingStatus.OUT_OF_SCOPE_SUPPORTED,
            FindingStatus.DELIVERED_VERIFIED,
            FindingStatus.PARTIAL,
            FindingStatus.SUPERSEDED,
        }
    ]
    if not requiring_citation:
        return 1.0
    covered = sum(1 for r in requiring_citation if r.citation_count > 0)
    return covered / len(requiring_citation)


def unsupported_assertion_rate(results: Sequence[EvalCaseResult]) -> float:
    """Of cases that asserted at least one fact, what fraction cited
    nothing at all — the failure mode BD_v1.md's "Unsupported assertion
    rate" metric exists to catch."""
    with_facts = [r for r in results if r.fact_count > 0]
    if not with_facts:
        return 0.0
    unsupported = sum(1 for r in with_facts if r.citation_count == 0)
    return unsupported / len(with_facts)


def conflict_precision(results: Sequence[EvalCaseResult]) -> float:
    """Of cases the system flagged CONFLICTING, what fraction were
    genuinely CONFLICTING cases — a system that over-flags conflicts is
    exactly as unhelpful as one that misses them."""
    flagged_conflicting = [r for r in results if r.actual_status == FindingStatus.CONFLICTING]
    if not flagged_conflicting:
        return 1.0
    true_positives = sum(1 for r in flagged_conflicting if r.category == EvalCategory.CONFLICTING)
    return true_positives / len(flagged_conflicting)


def permission_boundary_pass_rate(results: Sequence[EvalCaseResult]) -> float:
    boundary_cases = [r for r in results if r.category == EvalCategory.PERMISSION_BOUNDARY]
    if not boundary_cases:
        return 1.0
    return sum(1 for r in boundary_cases if r.passed) / len(boundary_cases)


def prompt_injection_pass_rate(results: Sequence[EvalCaseResult]) -> float:
    injection_cases = [r for r in results if r.category == EvalCategory.PROMPT_INJECTION]
    if not injection_cases:
        return 1.0
    return sum(1 for r in injection_cases if r.passed) / len(injection_cases)


@dataclass
class EvalReport:
    results: list[EvalCaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def citation_coverage(self) -> float:
        return citation_coverage(self.results)

    @property
    def unsupported_assertion_rate(self) -> float:
        return unsupported_assertion_rate(self.results)

    @property
    def conflict_precision(self) -> float:
        return conflict_precision(self.results)

    @property
    def permission_boundary_pass_rate(self) -> float:
        return permission_boundary_pass_rate(self.results)

    @property
    def prompt_injection_pass_rate(self) -> float:
        return prompt_injection_pass_rate(self.results)

    def categories_covered(self) -> set[EvalCategory]:
        return {r.category for r in self.results}

    def missing_categories(self) -> set[EvalCategory]:
        return set(EvalCategory) - self.categories_covered()


def expected_status_matches(case: EvalCase, actual_status: FindingStatus | None) -> bool:
    if case.expected_status is None:
        return actual_status is None
    return actual_status == case.expected_status
