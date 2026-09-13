"""`POST /api/v1/agent/runs`: creates the agent_runs row and enqueues the
bounded state machine (apps/ai_atlas/agent_runner) to run asynchronously.
The HTTP request returns as soon as the row exists — progress streams over
`GET /api/v1/agent/runs/{run_id}/events` (SSE), and the final result is
read back via `GET /api/v1/agent/runs/{run_id}` /
`GET /api/v1/findings/{finding_id}`.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.celery_client import enqueue_run_agent
from atlasai_db.models.agent import AgentRun
from atlasai_db.repositories.agent import AgentRunRepository


async def create_agent_run(
    session: AsyncSession, *, tenant_id: uuid.UUID, project_id: uuid.UUID, requested_by: uuid.UUID, question: str
) -> AgentRun:
    run_repo = AgentRunRepository(session, tenant_id=tenant_id, project_id=project_id)
    run = await run_repo.create(requested_by=requested_by, question=question)
    await session.commit()

    enqueue_run_agent(tenant_id=str(tenant_id), project_id=str(project_id), agent_run_id=str(run.id))
    return run
