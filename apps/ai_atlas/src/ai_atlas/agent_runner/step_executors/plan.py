"""PLAN: create subqueries and allowlisted tools (TD_v2.md §5).

Deterministic for this build (the question itself is the single subquery,
and the allowlist is the full read-tool set) rather than an additional LLM
call to decompose the question into sub-queries — a genuine query-
decomposition PLAN step is a natural upgrade once the evaluation harness
(packages/evaluation) shows it's worth the extra latency/cost for
multi-part questions. It is still a real, checkpointed state, not skipped.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_domain.agent.contracts import PlanOutput

READ_TOOLS = [
    "search_evidence",
    "get_source_record",
    "get_requirement_timeline",
    "compare_scope_versions",
    "analyze_conflict",
    "search_delivery_records",
]


async def run(ctx: StepContext, *, question: str) -> PlanOutput:
    started_at = datetime.now(UTC)
    result = PlanOutput(subqueries=[question], allowed_tools=list(READ_TOOLS), requires_action=False)

    await ctx.recorder.record(
        state_name="PLAN",
        status="SUCCEEDED",
        output_json=result.model_dump(mode="json"),
        started_at=started_at,
        summary=f"{len(result.subqueries)} subquery(ies)",
    )
    return result
