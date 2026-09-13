"""Celery entrypoint for the bounded agent state machine. `POST
/api/v1/agent/runs` (apps/api) creates the agent_runs row and enqueues
this task, then returns immediately — the run itself streams progress over
the realtime SSE channel rather than blocking the HTTP request.
"""

from __future__ import annotations

import asyncio
import uuid

from celery.utils.log import get_task_logger

from ai_atlas.agent_runner.runner import AgentRunner
from ai_atlas.celery_app import celery_app
from atlasai_db.engine import dispose_async_engine, get_async_sessionmaker

logger = get_task_logger(__name__)


async def _run(tenant_id: str, project_id: str, agent_run_id: str) -> None:
    try:
        session_factory = get_async_sessionmaker()
        async with session_factory() as session:
            runner = AgentRunner(session, tenant_id=uuid.UUID(tenant_id), project_id=uuid.UUID(project_id))
            await runner.run(uuid.UUID(agent_run_id))
    finally:
        # See atlasai_db.engine.dispose_async_engine's docstring: required
        # because each Celery task body runs asyncio.run() with its own
        # fresh event loop, and the cached async engine's connection pool
        # is bound to whichever loop created it.
        await dispose_async_engine()


def _run_agent_task(tenant_id: str, project_id: str, agent_run_id: str) -> None:
    try:
        asyncio.run(_run(tenant_id, project_id, agent_run_id))
    except Exception:
        logger.exception("agent run failed outside AgentRunner's own error handling: run_id=%s", agent_run_id)
        raise


run_agent_task = celery_app.task(name="ai_atlas.run_agent")(_run_agent_task)
