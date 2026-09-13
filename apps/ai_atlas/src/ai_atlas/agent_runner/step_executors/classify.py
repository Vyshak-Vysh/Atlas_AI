"""CLASSIFY: determine intent and risk (TD_v2.md §5). Uses the cheap
classify-tier model (Haiku by default) — this is a high-volume, low-
complexity step, exactly the workload the model-tiering design in
packages/llm_gateway exists for.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_domain.agent.contracts import ClassifyOutput
from atlasai_llm_gateway import AnthropicGateway

_CLASSIFY_SYSTEM_PROMPT = """You classify a question asked of AtlasAI, an evidence-backed project \
intelligence system. Given the question, determine:
- intent: one of SCOPE_QUESTION, DELIVERY_QUESTION, CONFLICT_CHECK, DRAFT_RESPONSE, EXPORT_REPORT
- risk_level: LOW, MEDIUM, or HIGH. HIGH means the answer could affect client-facing commitments, \
billing, or contractual obligations. MEDIUM means it affects internal planning. LOW is a routine \
informational lookup.
- rationale: one sentence explaining the classification.
"""


async def run(ctx: StepContext, *, question: str) -> ClassifyOutput:
    started_at = datetime.now(UTC)
    gateway = AnthropicGateway()
    try:
        completion = await gateway.complete_structured(
            system=_CLASSIFY_SYSTEM_PROMPT,
            user_content=f"Question: {question}",
            output_format=ClassifyOutput,
            model=gateway.model_for_classify(),
            max_tokens=500,
        )
    except Exception as exc:
        await ctx.recorder.record_failure(state_name="CLASSIFY", error=exc, started_at=started_at)
        raise
    finally:
        await gateway.aclose()

    result: ClassifyOutput = completion.parsed  # type: ignore[assignment]
    ctx.total_tokens_used += completion.usage.input_tokens + completion.usage.output_tokens

    await ctx.recorder.record(
        state_name="CLASSIFY",
        status="SUCCEEDED",
        input_json={"question": question},
        output_json=result.model_dump(mode="json"),
        started_at=started_at,
        token_count=completion.usage.input_tokens + completion.usage.output_tokens,
        summary=f"intent={result.intent.value} risk={result.risk_level}",
    )
    return result
