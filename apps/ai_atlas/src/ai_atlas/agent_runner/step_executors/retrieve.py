"""RETRIEVE: permission-filtered hybrid search (TD_v2.md §5). One
hybrid_candidates() call per PLAN subquery, each counted against the
run's per-tool call budget (RunLimits.max_calls_per_tool) — the same
search_evidence tool the agent's read-tool registry exposes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_domain.agent.contracts import PlanOutput, RetrieveOutput
from atlasai_retrieval import EmbedderClient, hybrid_candidates


class ToolBudgetExceededError(Exception):
    pass


async def run(ctx: StepContext, *, plan: PlanOutput) -> list[RetrieveOutput]:
    started_at = datetime.now(UTC)
    outputs: list[RetrieveOutput] = []

    embedder = EmbedderClient()
    try:
        for subquery in plan.subqueries:
            call_count = ctx.register_tool_call("search_evidence")
            if call_count > ctx.limits.max_calls_per_tool:
                raise ToolBudgetExceededError(
                    f"search_evidence exceeded its budget of {ctx.limits.max_calls_per_tool} calls in this run"
                )

            query_embedding = await embedder.embed_query(subquery)
            candidates = await hybrid_candidates(
                ctx.session,
                tenant_id=ctx.tenant_id,
                project_id=ctx.project_id,
                query_text=subquery,
                query_embedding=query_embedding,
            )
            outputs.append(RetrieveOutput(subquery=subquery, candidates=candidates))
    except Exception as exc:
        await ctx.recorder.record_failure(state_name="RETRIEVE", error=exc, started_at=started_at)
        raise
    finally:
        await embedder.aclose()

    total_candidates = sum(len(o.candidates) for o in outputs)
    await ctx.recorder.record(
        state_name="RETRIEVE",
        status="SUCCEEDED",
        tool_name="search_evidence",
        input_json={"subqueries": plan.subqueries},
        output_json={"candidate_count": total_candidates},
        started_at=started_at,
        summary=f"{total_candidates} candidate(s) across {len(plan.subqueries)} subquery(ies)",
    )
    return outputs
