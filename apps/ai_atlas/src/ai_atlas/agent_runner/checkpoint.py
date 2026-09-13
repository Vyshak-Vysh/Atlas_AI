"""The single choke point that writes agent_steps rows and publishes the
realtime event — every step executor calls through here rather than
writing agent_steps directly, so "commit, then publish" (never the other
order) is enforced in one place. Publishing after commit means a
subscriber can never observe an event for a step that isn't yet
independently queryable via `GET /api/v1/agent/runs/{run_id}` (implementation
plan §4).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.redis_client import agent_run_channel, get_redis_client
from atlasai_db.repositories.agent import AgentStepRepository
from atlasai_domain.agent.events import AgentStepEvent


class AgentStepRecorder:
    def __init__(self, session: AsyncSession, *, agent_run_id: uuid.UUID) -> None:
        self._session = session
        self._agent_run_id = agent_run_id
        self._step_repo = AgentStepRepository(session)

    async def record(
        self,
        *,
        state_name: str,
        status: str,
        tool_name: str | None = None,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        token_count: int | None = None,
        summary: str | None = None,
    ) -> int:
        finished_at = datetime.now(UTC)
        step_no = await self._step_repo.next_step_no(self._agent_run_id)
        latency_ms = int((finished_at - started_at).total_seconds() * 1000) if started_at else None

        await self._step_repo.record(
            agent_run_id=self._agent_run_id,
            step_no=step_no,
            state_name=state_name,
            status=status,
            tool_name=tool_name,
            input_json=input_json,
            output_json=output_json,
            started_at=started_at,
            finished_at=finished_at,
            token_count=token_count,
            latency_ms=latency_ms,
        )
        await self._session.commit()

        event = AgentStepEvent(
            run_id=str(self._agent_run_id),
            step_no=step_no,
            state_name=state_name,
            status=status,
            tool_name=tool_name,
            summary=summary,
            started_at=started_at,
            finished_at=finished_at,
        )
        client = get_redis_client()
        await client.publish(agent_run_channel(str(self._agent_run_id)), event.model_dump_json())

        return step_no

    async def record_failure(self, *, state_name: str, error: Exception, started_at: datetime) -> int:
        """Called from a step executor's `except` clause before re-raising,
        so a step that fails (not just a run that fails) leaves its own
        agent_steps row — "any state -> FAILED -> audited terminal state"
        (ATLASAI_MASTER_SPEC.md §4) applies at the step level, not only the
        run level."""
        return await self.record(
            state_name=state_name,
            status="FAILED",
            input_json=None,
            output_json={"error": str(error)},
            started_at=started_at,
            summary=f"{state_name} failed: {error}"[:200],
        )
