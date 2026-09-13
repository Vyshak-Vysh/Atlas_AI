"""Loads EvalCase fixtures from tests/evaluation/fixtures/*.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from atlasai_evaluation.schema import EvalCase


def load_fixture_file(path: Path) -> list[EvalCase]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    cases = raw if isinstance(raw, list) else raw.get("cases", [])
    return [EvalCase.model_validate(c) for c in cases]


def load_fixture_directory(directory: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for path in sorted(directory.glob("*.yaml")):
        cases.extend(load_fixture_file(path))
    return cases
