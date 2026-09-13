from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership_query
from atlasai_api.schemas.agent import AgentRunResponse, CreateAgentRunRequest
from atlasai_api.services.agent_service import create_agent_run
from atlasai_db.models.agent import AgentRun
from atlasai_db.redis_client import agent_run_channel, get_redis_client
from atlasai_db.repositories.agent import AgentRunRepository, AgentStepRepository

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

_HEARTBEAT_SECONDS = 15


def _to_response(run: AgentRun) -> AgentRunResponse:
    finding_id = None
    if isinstance(run.state_json, dict) and run.state_json.get("finding_id"):
        finding_id = uuid.UUID(run.state_json["finding_id"])
    error = run.error_json.get("message") if isinstance(run.error_json, dict) else None
    return AgentRunResponse(
        id=run.id,
        project_id=run.project_id,
        question=run.question,
        status=run.status,
        finding_id=finding_id,
        error=error,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


@router.post("/runs", response_model=AgentRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    body: CreateAgentRunRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRunResponse:
    run = await create_agent_run(
        session, tenant_id=ctx.tenant_id, project_id=ctx.project_id, requested_by=ctx.user.id, question=body.question
    )
    return _to_response(run)


@router.get("/runs", response_model=list[AgentRunResponse])
async def list_runs(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentRunResponse]:
    run_repo = AgentRunRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    runs = await run_repo.list_for_project(limit=limit, offset=offset)
    return [_to_response(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_run(
    run_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> AgentRunResponse:
    run_repo = AgentRunRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    run = await run_repo.get_by_id(run_id)
    return _to_response(run)


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: uuid.UUID,
    request: Request,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> EventSourceResponse:
    # Authorize before subscribing to anything — 404s the same way every
    # other project-scoped endpoint does if the run isn't in this project.
    run_repo = AgentRunRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    await run_repo.get_by_id(run_id)

    last_event_id = request.headers.get("last-event-id")
    after_step_no = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        client = get_redis_client()
        pubsub = client.pubsub()
        # Subscribe BEFORE the catch-up query — if a step is written in the
        # gap between subscribing and querying, it appears in the catch-up
        # query; if it's written after, it arrives on the live subscription.
        # Subscribing after the query (the other order) can silently drop a
        # step written in between.
        await pubsub.subscribe(agent_run_channel(str(run_id)))
        try:
            step_repo = AgentStepRepository(session)
            for step in await step_repo.list_from(run_id, after_step_no=after_step_no):
                yield {
                    "id": str(step.step_no),
                    "event": "step",
                    "data": json.dumps(
                        {
                            "step_no": step.step_no,
                            "state_name": step.state_name,
                            "status": step.status,
                            "tool_name": step.tool_name,
                        }
                    ),
                }
                if step.state_name == "COMPLETE" or step.status == "FAILED":
                    return

            while True:
                if await request.is_disconnected():
                    return
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=_HEARTBEAT_SECONDS)
                if message is None:
                    yield {"event": "heartbeat", "data": ""}
                    continue
                payload = json.loads(message["data"])
                yield {"id": str(payload["step_no"]), "event": "step", "data": message["data"]}
                if payload["state_name"] == "COMPLETE" or payload["status"] == "FAILED":
                    return
        finally:
            await pubsub.unsubscribe(agent_run_channel(str(run_id)))
            # redis-py's PubSub.aclose has no return type stub.
            await pubsub.aclose()  # type: ignore[no-untyped-call]

    return EventSourceResponse(event_generator())
