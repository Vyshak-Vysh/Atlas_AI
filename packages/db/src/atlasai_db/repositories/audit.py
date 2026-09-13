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

from atlasai_db.models.audit import AuditEvent
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
