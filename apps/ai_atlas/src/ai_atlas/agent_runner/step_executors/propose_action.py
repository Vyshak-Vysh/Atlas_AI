"""PROPOSE_ACTION: freeze the action payload and hash it (TD_v2.md §5,
BD_v2.md §7 "Every external action has an immutable payload. Approval is
bound to the exact payload hash.").

Creates the `actions` row with status WAITING_APPROVAL. Execution is never
inline here — it happens later, out of band, when a human calls `POST
/api/v1/actions/{id}/approve` (apps/api/services/action_service.py), which
is also where the frozen payload_hash is re-checked against whatever the
action's payload_json still is at approval time.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_db.models.actions import Action
from atlasai_db.repositories.actions import ActionRepository
from atlasai_domain.agent.contracts import ActionDecisionOutput
from atlasai_domain.contracts.actions import ActionPayload
from atlasai_security import hash_payload


async def run(ctx: StepContext, *, decision: ActionDecisionOutput) -> Action:
    started_at = datetime.now(UTC)
    if decision.action_type is None or decision.action_payload is None:
        raise ValueError("propose_action requires action_type and action_payload from ACTION_DECISION")

    payload = ActionPayload(
        action_type=decision.action_type, project_id=ctx.project_id, payload=decision.action_payload
    )
    payload_hash = hash_payload(payload)

    action_repo = ActionRepository(ctx.session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    action = await action_repo.create(
        created_by=ctx.agent_run.requested_by,
        action_type=decision.action_type.value,
        payload_json=decision.action_payload,
        idempotency_key=f"agent_run:{ctx.agent_run.id}:{decision.action_type.value}",
        payload_hash=payload_hash,
    )
    action = await action_repo.set_status(action, "WAITING_APPROVAL")
    await ctx.session.commit()

    await ctx.recorder.record(
        state_name="PROPOSE_ACTION",
        status="SUCCEEDED",
        output_json={"action_id": str(action.id), "action_type": action.action_type, "payload_hash": payload_hash},
        started_at=started_at,
        summary=f"action {action.id} proposed, awaiting approval",
    )
    return action
