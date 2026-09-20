from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership
from atlasai_api.schemas.sprints import (
    CreateSprintRequest,
    SprintDetailResponse,
    SprintResponse,
    UpdateSprintRequest,
)
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.requirements import RequirementRepository
from atlasai_db.repositories.tenancy import SprintRepository
from atlasai_domain.enums import AuditEventType, MembershipRole, SprintStatus, TaskStatus

router = APIRouter(prefix="/api/v1/projects/{project_id}/sprints", tags=["sprints"])

_SPRINT_MANAGER_ROLES = {MembershipRole.PROJECT_MANAGER, MembershipRole.AI_ENGINEER_ADMIN}


@router.post("", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
async def create_sprint(
    body: CreateSprintRequest,
    request: Request,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> SprintResponse:
    if ctx.role not in _SPRINT_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage sprints")
    sprint_repo = SprintRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    if await sprint_repo.get_by_number(body.sprint_number) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="a sprint with this number already exists"
        )

    sprint = await sprint_repo.create(
        name=body.name, sprint_number=body.sprint_number, start_date=body.start_date, end_date=body.end_date
    )
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.SPRINT_CREATED,
        actor_id=ctx.user.id,
        target_type="sprint",
        target_id=sprint.id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()
    return SprintResponse.model_validate(sprint)


@router.get("", response_model=list[SprintResponse])
async def list_sprints(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> list[SprintResponse]:
    sprint_repo = SprintRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    sprints = await sprint_repo.list_all(limit=limit, offset=offset)
    return [SprintResponse.model_validate(s) for s in sprints]


@router.get("/{sprint_id}", response_model=SprintDetailResponse)
async def get_sprint(
    sprint_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> SprintDetailResponse:
    sprint_repo = SprintRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    sprint = await sprint_repo.get_by_id(sprint_id)
    requirement_repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    tasks = await requirement_repo.list_for_project(sprint_id=sprint_id)
    done_count = sum(1 for t in tasks if t.task_status == TaskStatus.DONE)
    return SprintDetailResponse(
        sprint=SprintResponse.model_validate(sprint), task_count=len(tasks), done_count=done_count
    )


@router.patch("/{sprint_id}", response_model=SprintResponse)
async def update_sprint(
    sprint_id: uuid.UUID,
    body: UpdateSprintRequest,
    request: Request,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> SprintResponse:
    if ctx.role not in _SPRINT_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage sprints")

    new_status: str | None = None
    if body.status is not None:
        try:
            new_status = SprintStatus(body.status).value
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid status") from exc

    sprint_repo = SprintRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    sprint = await sprint_repo.get_by_id(sprint_id)
    sprint = await sprint_repo.update(
        sprint, name=body.name, start_date=body.start_date, end_date=body.end_date, status=new_status
    )
    event_type = (
        AuditEventType.SPRINT_COMPLETED if new_status == SprintStatus.COMPLETED.value else AuditEventType.SPRINT_UPDATED
    )
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=event_type,
        actor_id=ctx.user.id,
        target_type="sprint",
        target_id=sprint.id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()
    return SprintResponse.model_validate(sprint)
