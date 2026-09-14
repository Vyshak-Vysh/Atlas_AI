"""Repository for audit_events.

Used by every service that performs a sensitive action (BD_v2.md §9
requires audit coverage for access, search, sync, export, finding,
approval, and external-write events). Kept dependency-free of the
services that call it so it can be invoked from a single shared
`record_audit_event` helper without import cycles.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from atlasai_db.models.audit import AuditEvent
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.base import TenantScopedRepository


class AuditEventRepository(TenantScopedRepository[AuditEvent]):
    model = AuditEvent

    async def record(
        self,
        *,
        event_type: str,
        actor_id: uuid.UUID | None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
            metadata_=metadata or {},
        )
        return await self.add(event)

    async def list_recent(self, *, limit: int = 100, offset: int = 0) -> list[AuditEvent]:
        query = self._scoped_query().order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_target(
        self, *, target_type: str, target_id: uuid.UUID, limit: int = 200, offset: int = 0
    ) -> list[AuditEvent]:
        query = (
            self._scoped_query()
            .where(AuditEvent.target_type == target_type, AuditEvent.target_id == target_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_target_with_actor(
        self, *, target_type: str, target_id: uuid.UUID, limit: int = 200, offset: int = 0
    ) -> list[tuple[AuditEvent, User | None]]:
        """Outer join on User — actor_id is nullable (SET NULL on user
        deletion), so a history entry must still render for a departed
        user's past change rather than disappearing."""
        query = (
            select(AuditEvent, User)
            .outerjoin(User, User.id == AuditEvent.actor_id)
            .where(
                AuditEvent.tenant_id == self.tenant_id,
                AuditEvent.target_type == target_type,
                AuditEvent.target_id == target_id,
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return [(event, actor) for event, actor in result.all()]
