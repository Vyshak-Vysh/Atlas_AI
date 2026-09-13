"""Repositories for actions and approvals (BD_v2.md §7 approval rules)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.models.actions import Action, Approval
from atlasai_db.repositories.base import ProjectScopedRepository


class ActionRepository(ProjectScopedRepository[Action]):
    model = Action

    async def get_by_idempotency_key(self, idempotency_key: str) -> Action | None:
        query = self._scoped_query().where(Action.idempotency_key == idempotency_key)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self, *, created_by: uuid.UUID, action_type: str, payload_json: dict[str, Any],
        idempotency_key: str, payload_hash: str,
    ) -> Action:
        action = Action(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            created_by=created_by,
            action_type=action_type,
            payload_json=payload_json,
            status="PROPOSED",
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )
        return await self.add(action)

    async def set_status(self, action: Action, status: str) -> Action:
        action.status = status
        if status == "EXECUTED":
            action.executed_at = datetime.now(UTC)
        await self.session.flush()
        return action

    async def list_for_project(
        self, *, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Action]:
        query = self._scoped_query().order_by(Action.created_at.desc()).limit(limit).offset(offset)
        if status is not None:
            query = query.where(Action.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ApprovalRepository:
    """Reached through an already project-scoped Action."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_action(self, action_id: uuid.UUID) -> list[Approval]:
        result = await self.session.execute(select(Approval).where(Approval.action_id == action_id))
        return list(result.scalars().all())

    async def create(
        self, *, action_id: uuid.UUID, approver_id: uuid.UUID, decision: str, payload_hash: str,
        expires_at: datetime, reason: str | None = None,
    ) -> Approval:
        approval = Approval(
            action_id=action_id,
            approver_id=approver_id,
            decision=decision,
            reason=reason,
            payload_hash=payload_hash,
            expires_at=expires_at,
        )
        self.session.add(approval)
        await self.session.flush()
        return approval
