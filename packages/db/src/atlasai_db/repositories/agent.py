"""Repositories for agent_runs and agent_steps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.exceptions import NotFoundError
from atlasai_db.models.agent import AgentRun, AgentStep
from atlasai_db.repositories.base import ProjectScopedRepository


class AgentRunRepository(ProjectScopedRepository[AgentRun]):
    model = AgentRun

    async def create(
        self,
        *,
        requested_by: uuid.UUID,
        question: str,
        intent: str | None = None,
        model_policy: dict[str, Any] | None = None,
    ) -> AgentRun:
        run = AgentRun(
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            requested_by=requested_by,
            question=question,
            intent=intent,
            status="RECEIVED",
            model_policy=model_policy or {},
        )
        return await self.add(run)

    async def mark_started(self, run: AgentRun) -> AgentRun:
        run.status = "RUNNING"
        run.started_at = datetime.now(UTC)
        await self.session.flush()
        return run

    async def mark_finished(self, run: AgentRun, *, status: str, error_json: dict[str, Any] | None = None) -> AgentRun:
        run.status = status
        run.finished_at = datetime.now(UTC)
        run.error_json = error_json
        await self.session.flush()
        return run

    async def list_for_project(self, *, limit: int = 100, offset: int = 0) -> list[AgentRun]:
        query = self._scoped_query().order_by(AgentRun.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class AgentStepRepository:
    """Reached through an already project-scoped AgentRun."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, agent_run_id: uuid.UUID, step_id: uuid.UUID) -> AgentStep:
        result = await self.session.execute(
            select(AgentStep).where(AgentStep.agent_run_id == agent_run_id, AgentStep.id == step_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(AgentStep.__name__, step_id)
        return row

    async def next_step_no(self, agent_run_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(AgentStep.step_no)
            .where(AgentStep.agent_run_id == agent_run_id)
            .order_by(AgentStep.step_no.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        return (last or 0) + 1

    async def record(
        self, *, agent_run_id: uuid.UUID, step_no: int, state_name: str, status: str,
        tool_name: str | None = None,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        started_at: datetime | None = None, finished_at: datetime | None = None,
        token_count: int | None = None, latency_ms: int | None = None,
    ) -> AgentStep:
        step = AgentStep(
            agent_run_id=agent_run_id,
            step_no=step_no,
            state_name=state_name,
            tool_name=tool_name,
            input_json=input_json,
            output_json=output_json,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            token_count=token_count,
            latency_ms=latency_ms,
        )
        self.session.add(step)
        await self.session.flush()
        return step

    async def list_from(self, agent_run_id: uuid.UUID, *, after_step_no: int = 0) -> list[AgentStep]:
        result = await self.session.execute(
            select(AgentStep)
            .where(AgentStep.agent_run_id == agent_run_id, AgentStep.step_no > after_step_no)
            .order_by(AgentStep.step_no.asc())
        )
        return list(result.scalars().all())
