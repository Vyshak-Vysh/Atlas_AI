"""Generic repository base classes enforcing tenant/project scoping.

Design decision (see the implementation plan, "Tenant/project scoping"):
mandatory constructor arguments, not Postgres Row-Level Security. Every
query method built on top of these bases injects the tenant_id/project_id
filter itself — a caller cannot construct a query that skips it, and a
cross-tenant/cross-project lookup raises `NotFoundError` rather than
returning `None` or a distinct "forbidden" shape.

ERD_FINAL.md's tables are not uniform: some carry a real `tenant_id`
column (projects, connectors, source_records, evidence_chunks, agent_runs,
actions, audit_events), some carry only `project_id` (phases, requirements,
claims, decisions, delivery_records, findings), and several "child of a
scoped parent" tables (sync_runs, source_versions, agent_steps,
finding_citations, approvals, requirement_evidence) carry neither and must
be reached through their parent's id instead. `TenantScopedRepository` and
`ProjectScopedRepository` below are for the first two groups only; the third
group's repositories implement bespoke scoping by first loading the parent
through an already-scoped repository (see e.g. repositories/agent.py).

All repositories are async (AsyncSession) — including from apps/ai_atlas's
Celery tasks, which wrap their repository calls with `asyncio.run(...)`
rather than duplicating this layer as sync code. The sync engine in
`atlasai_db.engine` exists only for Alembic.
"""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.exceptions import NotFoundError

ModelT = TypeVar("ModelT")


class _RepositoryBase(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _scoped_query(self) -> Select[tuple[ModelT]]:
        raise NotImplementedError

    async def get_by_id(self, id_: uuid.UUID) -> ModelT:
        query = self._scoped_query().where(self.model.id == id_)  # type: ignore[attr-defined]
        result = await self.session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(self.model.__name__, id_)
        return row

    async def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        query = self._scoped_query().limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class TenantScopedRepository(_RepositoryBase[ModelT]):
    """For models with a real `tenant_id` column."""

    def __init__(self, session: AsyncSession, *, tenant_id: uuid.UUID) -> None:
        super().__init__(session)
        if tenant_id is None:
            raise ValueError("tenant_id is required — repositories never operate unscoped")
        self.tenant_id = tenant_id

    def _scoped_query(self) -> Select[tuple[ModelT]]:
        return select(self.model).where(self.model.tenant_id == self.tenant_id)  # type: ignore[attr-defined]


class ProjectScopedRepository(_RepositoryBase[ModelT]):
    """For models with a real `project_id` column. `tenant_id` is accepted
    and stored (callers must have already validated the project belongs to
    that tenant via ProjectRepository) but is not part of the SQL filter for
    models that have no tenant_id column of their own — project_id is a
    UUID primary key elsewhere, so filtering by it alone cannot cross a
    tenant boundary once the caller-supplied project_id has itself been
    validated against the tenant."""

    def __init__(self, session: AsyncSession, *, tenant_id: uuid.UUID, project_id: uuid.UUID) -> None:
        super().__init__(session)
        if tenant_id is None or project_id is None:
            raise ValueError("tenant_id and project_id are required — repositories never operate unscoped")
        self.tenant_id = tenant_id
        self.project_id = project_id

    def _scoped_query(self) -> Select[tuple[ModelT]]:
        return select(self.model).where(self.model.project_id == self.project_id)  # type: ignore[attr-defined]
