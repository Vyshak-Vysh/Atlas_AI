from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import (
    ProjectContext,
    check_tenant_membership,
    get_current_user,
    get_db_session,
    require_project_membership,
)
from atlasai_api.schemas.projects import (
    AddProjectMemberRequest,
    CreatePhaseRequest,
    CreateProjectRequest,
    PhaseResponse,
    ProjectMemberDetailResponse,
    ProjectMemberResponse,
    ProjectOverviewResponse,
    ProjectResponse,
    UpdateProjectRequest,
)
from atlasai_api.schemas.tenants import UpdateMemberRoleRequest
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.tenancy import (
    MembershipRepository,
    PhaseRepository,
    ProjectRepository,
    SpaceRepository,
    UserRepository,
)
from atlasai_domain.enums import AuditEventType, MembershipRole

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

_PROJECT_CREATOR_ROLES = {MembershipRole.PROJECT_MANAGER, MembershipRole.AI_ENGINEER_ADMIN}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: CreateProjectRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    role = await check_tenant_membership(session, tenant_id=body.tenant_id, user=user, request=request)
    if role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot create projects")

    if body.space_id is not None:
        # 404s (not silently ignored) if the space belongs to a different
        # tenant — prevents attaching a project to another tenant's space.
        await SpaceRepository(session, tenant_id=body.tenant_id).get_by_id(body.space_id)

    project_repo = ProjectRepository(session, tenant_id=body.tenant_id)
    project = await project_repo.create(
        name=body.name,
        client_name=body.client_name,
        code=body.code,
        timezone=body.timezone,
        space_id=body.space_id,
    )
    await MembershipRepository(session).add_project_member(
        project_id=project.id, user_id=user.id, role=role.value
    )
    await AuditEventRepository(session, tenant_id=body.tenant_id).record(
        event_type=AuditEventType.PROJECT_CREATED, actor_id=user.id, target_type="project", target_id=project.id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ProjectResponse]:
    await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)

    membership_repo = MembershipRepository(session)
    project_ids = await membership_repo.list_project_ids_for_user(tenant_id=tenant_id, user_id=user.id)
    if not project_ids:
        return []

    project_repo = ProjectRepository(session, tenant_id=tenant_id)
    projects = [await project_repo.get_by_id(pid) for pid in project_ids]
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}/overview", response_model=ProjectOverviewResponse)
async def get_project_overview(
    ctx: ProjectContext = Depends(require_project_membership), session: AsyncSession = Depends(get_db_session)
) -> ProjectOverviewResponse:
    project_repo = ProjectRepository(session, tenant_id=ctx.tenant_id)
    project = await project_repo.get_by_id(ctx.project_id)
    phase_repo = PhaseRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    phases = await phase_repo.list_all(limit=500)
    member_count = await MembershipRepository(session).count_project_members(ctx.project_id)
    return ProjectOverviewResponse(
        project=ProjectResponse.model_validate(project),
        phases=[PhaseResponse.model_validate(p) for p in phases],
        member_count=member_count,
    )


@router.post("/{project_id}/phases", response_model=PhaseResponse, status_code=status.HTTP_201_CREATED)
async def create_phase(
    body: CreatePhaseRequest,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> PhaseResponse:
    if ctx.role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage phases")
    phase_repo = PhaseRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    phase = await phase_repo.create(
        name=body.name, phase_number=body.phase_number, start_date=body.start_date, end_date=body.end_date
    )
    await session.commit()
    return PhaseResponse.model_validate(phase)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    body: AddProjectMemberRequest,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectMemberResponse:
    if ctx.role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage project members")

    try:
        role = MembershipRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid role") from exc

    target_user = await UserRepository(session).get_by_email(body.email)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no user with that email")

    membership_repo = MembershipRepository(session)
    if await membership_repo.get_tenant_role(tenant_id=ctx.tenant_id, user_id=target_user.id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="user is not a member of this project's tenant"
        )

    member = await membership_repo.add_project_member(
        project_id=ctx.project_id, user_id=target_user.id, role=role.value
    )
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.PROJECT_MEMBER_ADDED,
        actor_id=ctx.user.id,
        target_type="user",
        target_id=target_user.id,
        metadata={"project_id": str(ctx.project_id), "role": role.value},
    )
    await session.commit()
    return ProjectMemberResponse(project_id=member.project_id, user_id=member.user_id, role=member.role)


@router.get("/{project_id}/members", response_model=list[ProjectMemberDetailResponse])
async def list_project_members(
    ctx: ProjectContext = Depends(require_project_membership), session: AsyncSession = Depends(get_db_session)
) -> list[ProjectMemberDetailResponse]:
    rows = await MembershipRepository(session).list_project_members(ctx.project_id)
    return [
        ProjectMemberDetailResponse(
            project_id=member.project_id,
            user_id=member.user_id,
            email=str(user.email),
            display_name=user.display_name,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, user in rows
    ]


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
async def update_project_member_role(
    user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectMemberResponse:
    if ctx.role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage project members")
    try:
        role = MembershipRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid role") from exc

    member = await MembershipRepository(session).update_project_member_role(
        project_id=ctx.project_id, user_id=user_id, role=role.value
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.MEMBER_ROLE_UPDATED,
        actor_id=ctx.user.id,
        target_type="user",
        target_id=user_id,
        metadata={"project_id": str(ctx.project_id), "role": role.value, "scope": "project"},
    )
    await session.commit()
    return ProjectMemberResponse(project_id=member.project_id, user_id=member.user_id, role=member.role)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    user_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if ctx.role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage project members")
    if user_id == ctx.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot remove your own membership")

    removed = await MembershipRepository(session).remove_project_member(project_id=ctx.project_id, user_id=user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.MEMBER_REMOVED,
        actor_id=ctx.user.id,
        target_type="user",
        target_id=user_id,
        metadata={"project_id": str(ctx.project_id), "scope": "project"},
    )
    await session.commit()


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    body: UpdateProjectRequest,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectResponse:
    if ctx.role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot update this project")

    if body.space_id is not None:
        await SpaceRepository(session, tenant_id=ctx.tenant_id).get_by_id(body.space_id)

    project_repo = ProjectRepository(session, tenant_id=ctx.tenant_id)
    project = await project_repo.get_by_id(ctx.project_id)
    project = await project_repo.update(
        project, name=body.name, client_name=body.client_name, status=body.status, space_id=body.space_id
    )
    await session.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    request: Request,
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Permanently deletes the project and everything scoped to it — tasks,
    findings, agent runs, actions, connectors, phases, sprints, and project
    memberships all cascade at the database level (every child table's
    project_id FK is ON DELETE CASCADE). Evidence/source records are
    deliberately NOT touched: they live at the tenant level and are
    associated to projects via connector scopes (ADR-0008), since the same
    synced document can be in scope for more than one project — deleting
    one project must never delete evidence another project still relies
    on. The audit event is recorded (and committed) before the delete so
    "this project was deleted, by whom, when" survives in the tenant-wide
    audit trail even though the project row itself is gone afterward."""
    if ctx.role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot delete this project")

    project_repo = ProjectRepository(session, tenant_id=ctx.tenant_id)
    project = await project_repo.get_by_id(ctx.project_id)

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.PROJECT_DELETED,
        actor_id=ctx.user.id,
        target_type="project",
        target_id=project.id,
        metadata={"name": project.name},
        request_id=request.headers.get("x-request-id"),
    )
    await session.delete(project)
    await session.commit()
