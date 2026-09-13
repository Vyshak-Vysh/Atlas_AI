"""Repositories for connectors, connector_scopes, sync_runs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.models.connectors import Connector, ConnectorScope, SyncRun
from atlasai_db.repositories.base import TenantScopedRepository


class ConnectorRepository(TenantScopedRepository[Connector]):
    model = Connector

    async def list_by_provider(self, provider: str) -> list[Connector]:
        query = self._scoped_query().where(Connector.provider == provider)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_project(self, project_id: uuid.UUID) -> list[Connector]:
        query = (
            self._scoped_query()
            .join(ConnectorScope, ConnectorScope.connector_id == Connector.id)
            .where(ConnectorScope.project_id == project_id)
            .distinct()
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, *, provider: str, credential_ref: str, external_account_id: str | None = None) -> Connector:
        connector = Connector(
            tenant_id=self.tenant_id,
            provider=provider,
            credential_ref=credential_ref,
            external_account_id=external_account_id,
        )
        return await self.add(connector)

    async def set_status(self, connector: Connector, status: str) -> Connector:
        connector.status = status
        await self.session.flush()
        return connector


async def is_connector_scoped_to_project(
    session: AsyncSession, *, connector_id: uuid.UUID | None, project_id: uuid.UUID
) -> bool:
    """Used to authorize project-level access to a source_record, which
    carries only `connector_id` (not `project_id`) directly — see
    apps/api's upload_service.py module docstring for the full join-path
    rationale."""
    if connector_id is None:
        return False
    result = await session.execute(
        select(ConnectorScope.connector_id).where(
            ConnectorScope.connector_id == connector_id, ConnectorScope.project_id == project_id
        )
    )
    return result.scalar_one_or_none() is not None


class ConnectorScopeRepository:
    """Reached only through an already tenant-scoped Connector — see the
    module docstring in repositories/base.py on "child of a scoped parent"
    tables."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_connector(self, connector_id: uuid.UUID) -> list[ConnectorScope]:
        result = await self.session.execute(
            select(ConnectorScope).where(ConnectorScope.connector_id == connector_id)
        )
        return list(result.scalars().all())

    async def add(
        self,
        *,
        connector_id: uuid.UUID,
        project_id: uuid.UUID,
        scope_type: str,
        scope_external_id: str | None,
        scope_json: dict[str, Any],
    ) -> ConnectorScope:
        scope = ConnectorScope(
            connector_id=connector_id,
            project_id=project_id,
            scope_type=scope_type,
            scope_external_id=scope_external_id,
            scope_json=scope_json,
        )
        self.session.add(scope)
        await self.session.flush()
        return scope


class SyncRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start(self, *, connector_id: uuid.UUID, cursor_before: str | None) -> SyncRun:
        run = SyncRun(connector_id=connector_id, cursor_before=cursor_before, status="RUNNING")
        self.session.add(run)
        await self.session.flush()
        return run

    async def finish(
        self,
        run: SyncRun,
        *,
        status: str,
        cursor_after: str | None,
        items_seen: int,
        items_changed: int,
        error_json: dict[str, Any] | None = None,
    ) -> SyncRun:
        run.status = status
        run.cursor_after = cursor_after
        run.items_seen = items_seen
        run.items_changed = items_changed
        run.error_json = error_json
        run.finished_at = datetime.now(UTC)
        await self.session.flush()
        return run

    async def list_for_connector(self, connector_id: uuid.UUID, *, limit: int = 20) -> list[SyncRun]:
        result = await self.session.execute(
            select(SyncRun)
            .where(SyncRun.connector_id == connector_id)
            .order_by(SyncRun.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
