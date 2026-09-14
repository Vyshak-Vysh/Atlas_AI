from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership_query
from atlasai_api.schemas.requirements import (
    CreateCommentRequest,
    CreateRequirementRequest,
    DeliveryRecordResponse,
    RequirementCommentResponse,
    RequirementDetailResponse,
    RequirementEvidenceLinkResponse,
    RequirementHistoryEntryResponse,
    RequirementResponse,
    UpdateCommentRequest,
    UpdateRequirementRequest,
)
from atlasai_api.services.requirement_service import (
    CommentPermissionError,
    InvalidAssigneeError,
    RequirementHasEvidenceError,
    add_comment,
    delete_comment,
    delete_requirement,
    update_comment,
    update_requirement,
)
from atlasai_db.exceptions import NotFoundError
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.requirements import RequirementCommentRepository, RequirementRepository
from atlasai_db.repositories.tenancy import MembershipRepository
from atlasai_domain.enums import AuditEventType, RequirementStatus, TaskPriority, TaskStatus
from atlasai_security import Permission, role_has_permission

router = APIRouter(prefix="/api/v1/requirements", tags=["requirements"])


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    status_filter: str | None = Query(default=None, alias="status"),
    phase_id: uuid.UUID | None = Query(default=None),
    task_status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assignee_id: uuid.UUID | None = Query(default=None),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[RequirementResponse]:
    repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    requirements = await repo.list_for_project(
        status=status_filter, phase_id=phase_id, task_status=task_status, priority=priority, assignee_id=assignee_id
    )
    return [RequirementResponse.model_validate(r) for r in requirements]


@router.post("", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    body: CreateRequirementRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> RequirementResponse:
    if not role_has_permission(ctx.role, Permission.CREATE_TASK):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing permission: CREATE_TASK")

    try:
        req_status = RequirementStatus(body.status)
        task_status = TaskStatus(body.task_status)
        priority = TaskPriority(body.priority)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid status") from exc

    repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    if await repo.get_by_key(body.key) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="a requirement with this key already exists")

    if body.assignee_id is not None:
        role = await MembershipRepository(session).get_project_role(
            project_id=ctx.project_id, user_id=body.assignee_id
        )
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="assignee is not a member of this project"
            )

    requirement = await repo.create(
        key=body.key,
        title=body.title,
        status=req_status.value,
        phase_id=body.phase_id,
        description=body.description,
        acceptance_criteria=body.acceptance_criteria,
        task_status=task_status.value,
        priority=priority.value,
        assignee_id=body.assignee_id,
    )
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.REQUIREMENT_CREATED,
        actor_id=ctx.user.id,
        target_type="requirement",
        target_id=requirement.id,
        metadata={"key": requirement.key, "title": requirement.title},
    )
    await session.commit()
    return RequirementResponse.model_validate(requirement)


@router.get("/{requirement_id}", response_model=RequirementDetailResponse)
async def get_requirement(
    requirement_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> RequirementDetailResponse:
    repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    try:
        requirement = await repo.get_with_relations(requirement_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="requirement not found") from exc

    return RequirementDetailResponse(
        requirement=RequirementResponse.model_validate(requirement),
        evidence_links=[
            RequirementEvidenceLinkResponse(
                evidence_chunk_id=link.evidence_chunk_id,
                relation_type=link.relation_type,
                confidence=float(link.confidence) if link.confidence is not None else None,
                rationale=link.rationale,
            )
            for link in requirement.evidence_links
        ],
        delivery_records=[DeliveryRecordResponse.model_validate(record) for record in requirement.delivery_records],
    )


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def patch_requirement(
    requirement_id: uuid.UUID,
    body: UpdateRequirementRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> RequirementResponse:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no fields to update")

    required_permission = Permission.ASSIGN_TASK if "assignee_id" in changes else Permission.EDIT_TASK
    if not role_has_permission(ctx.role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"missing permission: {required_permission}"
        )

    enum_fields: tuple[tuple[str, type], ...] = (
        ("status", RequirementStatus),
        ("task_status", TaskStatus),
        ("priority", TaskPriority),
    )
    for enum_field, enum_type in enum_fields:
        if enum_field in changes and changes[enum_field] is not None:
            try:
                changes[enum_field] = enum_type(changes[enum_field]).value
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"invalid {enum_field}"
                ) from exc

    try:
        requirement = await update_requirement(
            session,
            tenant_id=ctx.tenant_id,
            project_id=ctx.project_id,
            requirement_id=requirement_id,
            actor_id=ctx.user.id,
            changes=changes,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="requirement not found") from exc
    except InvalidAssigneeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RequirementResponse.model_validate(requirement)


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_requirement(
    requirement_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if not role_has_permission(ctx.role, Permission.DELETE_TASK):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing permission: DELETE_TASK")

    try:
        await delete_requirement(
            session, tenant_id=ctx.tenant_id, project_id=ctx.project_id, requirement_id=requirement_id,
            actor_id=ctx.user.id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="requirement not found") from exc
    except RequirementHasEvidenceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{requirement_id}/comments", response_model=list[RequirementCommentResponse])
async def list_comments(
    requirement_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[RequirementCommentResponse]:
    # Confirms the requirement belongs to this (already-authorized) project
    # before returning any comment — same NotFoundError-only pattern as
    # every other project-scoped lookup in this codebase.
    try:
        await RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id).get_by_id(
            requirement_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="requirement not found") from exc

    rows = await RequirementCommentRepository(session).list_for_requirement(requirement_id)
    return [
        RequirementCommentResponse(
            id=comment.id,
            requirement_id=comment.requirement_id,
            author_id=comment.author_id,
            author_display_name=author.display_name,
            author_email=str(author.email),
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
        for comment, author in rows
    ]


@router.post(
    "/{requirement_id}/comments", response_model=RequirementCommentResponse, status_code=status.HTTP_201_CREATED
)
async def create_comment(
    requirement_id: uuid.UUID,
    body: CreateCommentRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> RequirementCommentResponse:
    if not role_has_permission(ctx.role, Permission.COMMENT_ON_TASK):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing permission: COMMENT_ON_TASK")

    try:
        comment = await add_comment(
            session, tenant_id=ctx.tenant_id, project_id=ctx.project_id, requirement_id=requirement_id,
            actor_id=ctx.user.id, body=body.body,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="requirement not found") from exc

    return RequirementCommentResponse(
        id=comment.id,
        requirement_id=comment.requirement_id,
        author_id=comment.author_id,
        author_display_name=ctx.user.display_name,
        author_email=str(ctx.user.email),
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.patch("/{requirement_id}/comments/{comment_id}", response_model=RequirementCommentResponse)
async def edit_comment(
    requirement_id: uuid.UUID,
    comment_id: uuid.UUID,
    body: UpdateCommentRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> RequirementCommentResponse:
    if not role_has_permission(ctx.role, Permission.COMMENT_ON_TASK):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing permission: COMMENT_ON_TASK")

    try:
        comment = await update_comment(
            session, tenant_id=ctx.tenant_id, project_id=ctx.project_id, requirement_id=requirement_id,
            comment_id=comment_id, actor_id=ctx.user.id, actor_role=ctx.role, body=body.body,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found") from exc
    except CommentPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return RequirementCommentResponse(
        id=comment.id,
        requirement_id=comment.requirement_id,
        author_id=comment.author_id,
        author_display_name=ctx.user.display_name,
        author_email=str(ctx.user.email),
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.delete("/{requirement_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_comment(
    requirement_id: uuid.UUID,
    comment_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if not role_has_permission(ctx.role, Permission.COMMENT_ON_TASK):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="missing permission: COMMENT_ON_TASK")

    try:
        await delete_comment(
            session, tenant_id=ctx.tenant_id, project_id=ctx.project_id, requirement_id=requirement_id,
            comment_id=comment_id, actor_id=ctx.user.id, actor_role=ctx.role,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found") from exc
    except CommentPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{requirement_id}/history", response_model=list[RequirementHistoryEntryResponse])
async def get_history(
    requirement_id: uuid.UUID,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[RequirementHistoryEntryResponse]:
    """Visible to every project role, including CLIENT_VIEWER — read-only
    'who changed what, when' on content the viewer can already see in full
    (title/description/status), same trust tier as BR-016 evidence
    redaction, which is scoped to AI-drafted evidence content, not
    first-party task metadata. See the plan's BR-016 analysis."""
    try:
        await RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id).get_by_id(
            requirement_id
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="requirement not found") from exc

    rows = await AuditEventRepository(session, tenant_id=ctx.tenant_id).list_for_target_with_actor(
        target_type="requirement", target_id=requirement_id, limit=limit, offset=offset
    )
    return [
        RequirementHistoryEntryResponse(
            id=event.id,
            event_type=event.event_type,
            field=event.metadata_.get("field"),
            old_value=event.metadata_.get("old_value"),
            new_value=event.metadata_.get("new_value"),
            actor_id=event.actor_id,
            actor_display_name=actor.display_name if actor else None,
            actor_email=str(actor.email) if actor else None,
            created_at=event.created_at,
            metadata=event.metadata_,
        )
        for event, actor in rows
    ]
