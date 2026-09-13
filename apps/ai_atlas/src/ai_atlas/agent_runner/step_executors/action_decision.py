"""ACTION_DECISION: determine whether a write is requested (TD_v2.md §5).

Routes into the action branch only for the DRAFT_RESPONSE intent
(CLASSIFY's output) — a genuine, testable path through PROPOSE_ACTION ->
WAIT_APPROVAL -> EXECUTE rather than a fuller autonomous-intent-detection
system, which is out of scope for this build. Every other intent resolves
to `requires_action=False`, matching BD_v1.md's non-goal of automatically
sending anything without a human in the loop.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_domain.agent.contracts import ActionDecisionOutput, ClassifyOutput
from atlasai_domain.contracts.findings import FindingOutput
from atlasai_domain.enums import ActionType, AgentRunIntent


async def run(ctx: StepContext, *, classify_output: ClassifyOutput, finding: FindingOutput) -> ActionDecisionOutput:
    started_at = datetime.now(UTC)

    if classify_output.intent == AgentRunIntent.DRAFT_RESPONSE:
        result = ActionDecisionOutput(
            requires_action=True,
            action_type=ActionType.DRAFT_CLIENT_RESPONSE,
            reason="Question intent classified as DRAFT_RESPONSE.",
            action_payload={
                "question": ctx.agent_run.question,
                "draft_body": finding.summary,
                "based_on_finding_status": finding.status.value,
                "citation_count": len(finding.citations),
            },
            project_id=ctx.project_id,
        )
    else:
        result = ActionDecisionOutput(
            requires_action=False, reason=f"Intent {classify_output.intent.value} does not require an external write."
        )

    await ctx.recorder.record(
        state_name="ACTION_DECISION",
        status="SUCCEEDED",
        output_json=result.model_dump(mode="json"),
        started_at=started_at,
        summary="action requested" if result.requires_action else "no action requested",
    )
    return result
