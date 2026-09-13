"""Fixture-driven evaluation harness: the 9 required case categories
(in-scope, out-of-scope, conflicting, ambiguous, not-verified, superseded,
partially-delivered, prompt-injection, permission-boundary) run through the
real POST /api/v1/agent/runs path and scored against recall@k, citation
coverage, unsupported-assertion rate, and conflict precision."""

from atlasai_evaluation.loader import load_fixture_directory, load_fixture_file
from atlasai_evaluation.metrics import EvalCaseResult, EvalReport
from atlasai_evaluation.runner import EvalHarness
from atlasai_evaluation.schema import EvalCase, EvalCategory, EvalEvidenceFixture

__all__ = [
    "EvalCase",
    "EvalCaseResult",
    "EvalCategory",
    "EvalEvidenceFixture",
    "EvalHarness",
    "EvalReport",
    "load_fixture_directory",
    "load_fixture_file",
]
