from __future__ import annotations

import datetime
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import check_tenant_membership, get_current_user, get_db_session
from atlasai_api.routers.findings import finding_to_response
from atlasai_api.schemas.actions import ActionResponse
from atlasai_api.schemas.projects import ProjectResponse
from atlasai_api.schemas.spaces import (
    CreateSpaceRequest,
    SpaceActionItem,
    SpaceFindingItem,
    SpaceFindingStatusCount,
    SpaceOverviewResponse,
    SpaceProjectSummary,
    SpaceReportResponse,
    SpaceResponse,
    UpdateSpaceRequest,
)
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.actions import ActionRepository
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.findings import FindingRepository
from atlasai_db.repositories.requirements import RequirementRepository
from atlasai_db.repositories.tenancy import ProjectRepository, SpaceRepository
from atlasai_domain.enums import ActionStatus, AuditEventType, MembershipRole, RequirementStatus, SpaceStatus

router = APIRouter(prefix="/api/v1/spaces", tags=["spaces"])

_RECENT_FINDINGS_LIMIT = 20

_SPACE_MANAGER_ROLES = {MembershipRole.PROJECT_MANAGER, MembershipRole.AI_ENGINEER_ADMIN}


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(
    body: CreateSpaceRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SpaceResponse:
    role = await check_tenant_membership(session, tenant_id=body.tenant_id, user=user, request=request)
    if role not in _SPACE_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot create spaces")

    space_repo = SpaceRepository(session, tenant_id=body.tenant_id)
    if await space_repo.get_by_name(body.name) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="a space with this name already exists")

    space = await space_repo.create(name=body.name, description=body.description, color=body.color)
    await AuditEventRepository(session, tenant_id=body.tenant_id).record(
        event_type=AuditEventType.SPACE_CREATED,
        actor_id=user.id,
        target_type="space",
        target_id=space.id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()
    return SpaceResponse.model_validate(space)


@router.get("", response_model=list[SpaceResponse])
async def list_spaces(
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SpaceResponse]:
    await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    spaces = await space_repo.list_all(limit=limit, offset=offset)
    return [SpaceResponse.model_validate(s) for s in spaces]


@router.get("/{space_id}", response_model=SpaceOverviewResponse)
async def get_space_overview(
    space_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SpaceOverviewResponse:
    await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    space = await space_repo.get_by_id(space_id)
    project_count = await space_repo.count_projects(space_id)
    return SpaceOverviewResponse(space=SpaceResponse.model_validate(space), project_count=project_count)


@router.get("/{space_id}/projects", response_model=list[ProjectResponse])
async def list_space_projects(
    space_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ProjectResponse]:
    await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    await space_repo.get_by_id(space_id)  # 404s if the space doesn't belong to this tenant
    project_repo = ProjectRepository(session, tenant_id=tenant_id)
    projects = await project_repo.list_by_space(space_id)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.patch("/{space_id}", response_model=SpaceResponse)
async def update_space(
    space_id: uuid.UUID,
    body: UpdateSpaceRequest,
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SpaceResponse:
    role = await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    if role not in _SPACE_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot update this space")

    new_status: str | None = None
    if body.status is not None:
        try:
            new_status = SpaceStatus(body.status).value
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid status") from exc

    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    space = await space_repo.get_by_id(space_id)
    if body.name is not None and body.name != space.name and await space_repo.get_by_name(body.name) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="a space with this name already exists")

    space = await space_repo.update(
        space, name=body.name, description=body.description, color=body.color, status=new_status
    )
    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.SPACE_UPDATED,
        actor_id=user.id,
        target_type="space",
        target_id=space.id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()
    return SpaceResponse.model_validate(space)


@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space(
    space_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    role = await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    if role not in _SPACE_MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot delete this space")
    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    space = await space_repo.get_by_id(space_id)
    project_count = await space_repo.count_projects(space_id)
    if project_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="space still has projects assigned to it"
        )
    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.SPACE_DELETED,
        actor_id=user.id,
        target_type="space",
        target_id=space.id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.delete(space)
    await session.commit()


# --- Space-level rollups --------------------------------------------------
# Findings/Approvals/Reports previously existed only per-project (one
# engagement at a time) or per-workspace (every client mixed together) —
# nothing answered "how is THIS client doing across all their projects".
# These three endpoints fan out across the space's own projects, reusing
# the same project-scoped repository methods every per-project page already
# relies on (bounded by however many projects one space has), rather than
# writing new cross-project SQL — the aggregation happens here, in Python,
# over already-correct, already-tested per-project queries.


@router.get("/{space_id}/findings", response_model=list[SpaceFindingItem])
async def list_space_findings(
    space_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SpaceFindingItem]:
    await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    await space_repo.get_by_id(space_id)  # 404s if the space doesn't belong to this tenant
    project_repo = ProjectRepository(session, tenant_id=tenant_id)
    projects = await project_repo.list_by_space(space_id)

    items: list[SpaceFindingItem] = []
    for project in projects:
        project_response = ProjectResponse.model_validate(project)
        finding_repo = FindingRepository(session, tenant_id=tenant_id, project_id=project.id)
        findings = await finding_repo.list_for_project(status=status_filter, limit=limit)
        items.extend(SpaceFindingItem(project=project_response, finding=finding_to_response(f)) for f in findings)

    items.sort(key=lambda item: item.finding.created_at, reverse=True)
    return items[:limit]


@router.get("/{space_id}/actions", response_model=list[SpaceActionItem])
async def list_space_actions(
    space_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SpaceActionItem]:
    await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    await space_repo.get_by_id(space_id)
    project_repo = ProjectRepository(session, tenant_id=tenant_id)
    projects = await project_repo.list_by_space(space_id)

    items: list[SpaceActionItem] = []
    for project in projects:
        project_response = ProjectResponse.model_validate(project)
        action_repo = ActionRepository(session, tenant_id=tenant_id, project_id=project.id)
        actions = await action_repo.list_for_project(status=status_filter, limit=limit)
        items.extend(
            SpaceActionItem(project=project_response, action=ActionResponse.model_validate(a)) for a in actions
        )

    items.sort(key=lambda item: item.action.created_at, reverse=True)
    return items[:limit]


@router.get("/{space_id}/report", response_model=SpaceReportResponse)
async def get_space_report(
    space_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SpaceReportResponse:
    await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    space_repo = SpaceRepository(session, tenant_id=tenant_id)
    space = await space_repo.get_by_id(space_id)
    project_repo = ProjectRepository(session, tenant_id=tenant_id)
    projects = await project_repo.list_by_space(space_id)

    project_summaries: list[SpaceProjectSummary] = []
    all_findings: list[SpaceFindingItem] = []
    status_counts: Counter[str] = Counter()
    total_requirements = 0
    requirements_delivered = 0
    total_findings = 0
    total_pending_approvals = 0

    for project in projects:
        project_response = ProjectResponse.model_validate(project)

        requirement_repo = RequirementRepository(session, tenant_id=tenant_id, project_id=project.id)
        requirements = await requirement_repo.list_for_project()
        delivered = sum(1 for r in requirements if r.status == RequirementStatus.DELIVERED_VERIFIED.value)

        finding_repo = FindingRepository(session, tenant_id=tenant_id, project_id=project.id)
        findings = await finding_repo.list_for_project(limit=500)
        status_counts.update(f.status for f in findings)
        all_findings.extend(
            SpaceFindingItem(project=project_response, finding=finding_to_response(f)) for f in findings
        )

        action_repo = ActionRepository(session, tenant_id=tenant_id, project_id=project.id)
        pending_actions = await action_repo.list_for_project(status=ActionStatus.WAITING_APPROVAL.value, limit=500)

        project_summaries.append(
            SpaceProjectSummary(
                project=project_response,
                total_requirements=len(requirements),
                requirements_delivered=delivered,
                total_findings=len(findings),
                pending_approvals=len(pending_actions),
            )
        )
        total_requirements += len(requirements)
        requirements_delivered += delivered
        total_findings += len(findings)
        total_pending_approvals += len(pending_actions)

    all_findings.sort(key=lambda item: item.finding.created_at, reverse=True)

    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.REPORT_GENERATED,
        actor_id=user.id,
        target_type="space",
        target_id=space_id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()

    return SpaceReportResponse(
        space=SpaceResponse.model_validate(space),
        generated_at=datetime.datetime.now(datetime.UTC),
        project_count=len(projects),
        total_requirements=total_requirements,
        requirements_delivered=requirements_delivered,
        total_findings=total_findings,
        findings_by_status=[SpaceFindingStatusCount(status=s, count=c) for s, c in status_counts.items()],
        total_pending_approvals=total_pending_approvals,
        projects=project_summaries,
        recent_findings=all_findings[:_RECENT_FINDINGS_LIMIT],
    )
