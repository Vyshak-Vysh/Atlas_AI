"""ANALYZE: extract claims, events, requirements, and conflicts (TD_v2.md
§5). Implemented as one structured LLM call producing the full draft
finding (facts/inferences/contradictions/citations) — see
packages/llm_gateway/grounded_answer.py — rather than a separate claim-by-
claim extraction pass; VERIFY (the next state) re-validates its citations
and structural invariants before FINDING persists it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_domain.contracts.evidence import EvidenceCandidate
from atlasai_domain.contracts.findings import FindingOutput
from atlasai_llm_gateway.client import StructuredCompletion
from atlasai_llm_gateway.grounded_answer import generate_grounded_answer


async def run(
    ctx: StepContext, *, question: str, ranked_candidates: list[EvidenceCandidate]
) -> tuple[FindingOutput, StructuredCompletion]:
    started_at = datetime.now(UTC)

    try:
        finding, completion = await generate_grounded_answer(
            question=question, project_id=ctx.project_id, candidates=ranked_candidates
        )
    except Exception as exc:
        await ctx.recorder.record_failure(state_name="ANALYZE", error=exc, started_at=started_at)
        raise
    ctx.total_tokens_used += completion.usage.input_tokens + completion.usage.output_tokens

    await ctx.recorder.record(
        state_name="ANALYZE",
        status="SUCCEEDED",
        output_json={
            "status": finding.status.value,
            "fact_count": len(finding.facts),
            "contradiction_count": len(finding.contradictions),
            "citation_count": len(finding.citations),
        },
        started_at=started_at,
        token_count=completion.usage.input_tokens + completion.usage.output_tokens,
        summary=f"draft status={finding.status.value}",
    )
    return finding, completion
