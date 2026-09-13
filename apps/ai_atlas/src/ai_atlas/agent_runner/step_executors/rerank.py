"""RERANK: dedupe, score, and diversify evidence across all subqueries
(TD_v2.md §5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_domain.agent.contracts import EvidenceCandidate, RerankOutput, RetrieveOutput
from atlasai_retrieval import rerank as rerank_candidates

_TOP_N = 10


async def run(ctx: StepContext, *, question: str, retrieve_outputs: list[RetrieveOutput]) -> RerankOutput:
    started_at = datetime.now(UTC)

    by_id: dict[uuid.UUID, EvidenceCandidate] = {}
    duplicate_count = 0
    for output in retrieve_outputs:
        for candidate in output.candidates:
            if candidate.evidence_chunk_id in by_id:
                duplicate_count += 1
            else:
                by_id[candidate.evidence_chunk_id] = candidate

    ranked = rerank_candidates(list(by_id.values()), query_text=question, top_n=_TOP_N)
    result = RerankOutput(ranked=ranked, dropped_duplicate_count=duplicate_count)

    await ctx.recorder.record(
        state_name="RERANK",
        status="SUCCEEDED",
        output_json={"ranked_count": len(ranked), "dropped_duplicate_count": duplicate_count},
        started_at=started_at,
        summary=f"{len(ranked)} chunk(s) after rerank",
    )
    return result
