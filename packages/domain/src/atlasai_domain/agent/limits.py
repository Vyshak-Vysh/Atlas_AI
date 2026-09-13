"""Bounded-run safety limits (ATLASAI_MASTER_SPEC.md §4 / TD_v2.md §5).

Defaults come from environment-driven settings in the consuming app (apps/
ai_atlas reads AGENT_* env vars into its own Settings and constructs this),
never hardcoded at a call site. A run may narrow (never widen) these via
`agent_runs.model_policy` jsonb.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunLimits(BaseModel):
    max_steps: int = Field(default=12, ge=1, le=12)
    max_calls_per_tool: int = Field(default=3, ge=1, le=3)
    run_timeout_seconds: int = Field(default=180, ge=1)
    tool_timeout_seconds: int = Field(default=30, ge=1)
    token_budget: int = Field(default=200_000, ge=1)

    def narrowed_by(self, override: RunLimits) -> RunLimits:
        """Combine with a per-run override — the tighter of each field
        always wins, so a run can only ever narrow the global defaults."""
        return RunLimits(
            max_steps=min(self.max_steps, override.max_steps),
            max_calls_per_tool=min(self.max_calls_per_tool, override.max_calls_per_tool),
            run_timeout_seconds=min(self.run_timeout_seconds, override.run_timeout_seconds),
            tool_timeout_seconds=min(self.tool_timeout_seconds, override.tool_timeout_seconds),
            token_budget=min(self.token_budget, override.token_budget),
        )
