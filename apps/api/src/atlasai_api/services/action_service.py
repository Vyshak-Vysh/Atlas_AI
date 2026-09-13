"""Action approval/rejection/execution (BD_v2.md §7 approval rules).

Execution runs synchronously inside the approve call for the one action
type this build actually executes (DRAFT_CLIENT_RESPONSE — trivial, no
external system involved) rather than round-tripping through another
Celery task; SEND_EMAIL fails closed with a clear audit entry since no
outbound connector is configured by default (BD_v1.md's explicit non-goal
of auto-sending in the first release).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.models.actions import Action
from atlasai_db.repositories.actions import ActionRepository, ApprovalRepository
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_domain.enums import ActionType, AuditEventType

_APPROVAL_VALIDITY = timedelta(minutes=15)


class ActionNotApprovableError(Exception):
    pass


class PayloadHashMismatchError(Exception):
    pass


class ApprovalExpiredError(Exception):
    pass


@dataclass(frozen=True)
class ActionDecisionResult:
    action: Action
    execution_error: str | None = None


async def approve_action(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    action_id: uuid.UUID,
    approver_id: uuid.UUID,
    reason: str | None,
    expected_payload_hash: str | None,
) -> ActionDecisionResult:
    action_repo = ActionRepository(session, tenant_id=tenant_id, project_id=project_id)
    action = await action_repo.get_by_id(action_id)

    if action.status != "WAITING_APPROVAL":
        raise ActionNotApprovableError(f"action {action_id} is not awaiting approval (status={action.status})")

    if expected_payload_hash is not None and expected_payload_hash != action.payload_hash:
        raise PayloadHashMismatchError("the action's payload has changed since it was proposed")

    expires_at = datetime.now(UTC) + _APPROVAL_VALIDITY
    await ApprovalRepository(session).create(
        action_id=action.id,
        approver_id=approver_id,
        decision="APPROVED",
        payload_hash=action.payload_hash,
        expires_at=expires_at,
        reason=reason,
    )
    action = await action_repo.set_status(action, "APPROVED")
    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.ACTION_APPROVED, actor_id=approver_id, target_type="action", target_id=action.id
    )
    await session.commit()

    return await _execute(session, action=action, tenant_id=tenant_id, project_id=project_id, actor_id=approver_id)


async def reject_action(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    action_id: uuid.UUID,
    approver_id: uuid.UUID,
    reason: str | None,
) -> Action:
    action_repo = ActionRepository(session, tenant_id=tenant_id, project_id=project_id)
    action = await action_repo.get_by_id(action_id)

    if action.status != "WAITING_APPROVAL":
        raise ActionNotApprovableError(f"action {action_id} is not awaiting approval (status={action.status})")

    await ApprovalRepository(session).create(
        action_id=action.id,
        approver_id=approver_id,
        decision="REJECTED",
        payload_hash=action.payload_hash,
        expires_at=datetime.now(UTC),
        reason=reason,
    )
    action = await action_repo.set_status(action, "REJECTED")
    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.ACTION_REJECTED, actor_id=approver_id, target_type="action", target_id=action.id
    )
    await session.commit()
    return action


async def _execute(
    session: AsyncSession, *, action: Action, tenant_id: uuid.UUID, project_id: uuid.UUID, actor_id: uuid.UUID
) -> ActionDecisionResult:
    action_repo = ActionRepository(session, tenant_id=tenant_id, project_id=project_id)
    audit_repo = AuditEventRepository(session, tenant_id=tenant_id)

    # Re-validated at execution time, not just at approval time (ERD_FINAL.md
    # critical integrity rule #5: "An approval must be unexpired at execution
    # time"). Execution is synchronous and immediate here, so this can only
    # fail if _APPROVAL_VALIDITY were ever misconfigured to be non-positive.
    approvals = await ApprovalRepository(session).list_for_action(action.id)
    latest_approval = max(approvals, key=lambda a: a.decided_at)
    if latest_approval.expires_at < datetime.now(UTC):
        action = await action_repo.set_status(action, "EXPIRED")
        await audit_repo.record(
            event_type=AuditEventType.ACTION_EXECUTION_FAILED,
            actor_id=actor_id,
            target_type="action",
            target_id=action.id,
            metadata={"reason": "approval expired before execution"},
        )
        await session.commit()
        raise ApprovalExpiredError(f"approval for action {action.id} expired before execution")

    action = await action_repo.set_status(action, "EXECUTING")
    await session.commit()

    if action.action_type == ActionType.DRAFT_CLIENT_RESPONSE.value:
        action = await action_repo.set_status(action, "EXECUTED")
        await audit_repo.record(
            event_type=AuditEventType.ACTION_EXECUTED, actor_id=actor_id, target_type="action", target_id=action.id
        )
        await session.commit()
        return ActionDecisionResult(action=action)

    if action.action_type == ActionType.SEND_EMAIL.value:
        action = await action_repo.set_status(action, "FAILED")
        error = "no outbound email connector is configured — send_email fails closed by design"
        await audit_repo.record(
            event_type=AuditEventType.ACTION_EXECUTION_FAILED,
            actor_id=actor_id,
            target_type="action",
            target_id=action.id,
            metadata={"reason": error},
        )
        await session.commit()
        return ActionDecisionResult(action=action, execution_error=error)

    action = await action_repo.set_status(action, "FAILED")
    error = f"no EXECUTE handler implemented for action_type={action.action_type}"
    await audit_repo.record(
        event_type=AuditEventType.ACTION_EXECUTION_FAILED,
        actor_id=actor_id,
        target_type="action",
        target_id=action.id,
        metadata={"reason": error},
    )
    await session.commit()
    return ActionDecisionResult(action=action, execution_error=error)
