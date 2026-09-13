"""Unit tests for the evaluation fixture loader and metrics — pure,
no live stack or LLM required."""

from __future__ import annotations

from pathlib import Path

from atlasai_domain.enums import FindingStatus
from atlasai_evaluation import EvalCaseResult, EvalCategory, EvalReport, load_fixture_directory

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "evaluation" / "fixtures"


def test_fixture_directory_covers_all_nine_required_categories() -> None:
    cases = load_fixture_directory(FIXTURES_DIR)
    categories = {c.category for c in cases}
    assert categories == set(EvalCategory), f"missing categories: {set(EvalCategory) - categories}"


def test_every_case_has_a_unique_id() -> None:
    cases = load_fixture_directory(FIXTURES_DIR)
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))


def test_non_permission_boundary_cases_have_evidence_and_expected_status() -> None:
    cases = load_fixture_directory(FIXTURES_DIR)
    for case in cases:
        if case.category == EvalCategory.PERMISSION_BOUNDARY:
            continue
        assert case.evidence, f"{case.id} has no evidence fixtures"
        assert case.expected_status is not None, f"{case.id} has no expected_status"


def test_eval_report_flags_missing_categories() -> None:
    report = EvalReport(
        results=[
            EvalCaseResult(
                case_id="x",
                category=EvalCategory.IN_SCOPE,
                passed=True,
                actual_status=FindingStatus.IN_SCOPE_SUPPORTED,
            )
        ]
    )
    missing = report.missing_categories()
    assert EvalCategory.CONFLICTING in missing
    assert EvalCategory.IN_SCOPE not in missing


def test_eval_report_pass_rate() -> None:
    report = EvalReport(
        results=[
            EvalCaseResult(case_id="a", category=EvalCategory.IN_SCOPE, passed=True),
            EvalCaseResult(case_id="b", category=EvalCategory.OUT_OF_SCOPE, passed=False),
        ]
    )
    assert report.pass_rate == 0.5
