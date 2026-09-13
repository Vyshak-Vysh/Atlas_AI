from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership_query
from atlasai_api.schemas.actions import ActionResponse, ApproveActionRequest, RejectActionRequest
from atlasai_api.services.action_service import (
    ActionNotApprovableError,
    ApprovalExpiredError,
    PayloadHashMismatchError,
    approve_action,
    reject_action,
)
from atlasai_db.repositories.actions import ActionRepository
from atlasai_security import Permission, role_has_permission

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])


def _require_approver(ctx: ProjectContext) -> None:
    if not role_has_permission(ctx.role, Permission.APPROVE_ACTION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot approve or reject actions")


@router.get("", response_model=list[ActionResponse])
async def list_actions(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[ActionResponse]:
    action_repo = ActionRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    actions = await action_repo.list_for_project(status=status_filter, limit=limit, offset=offset)
    return [ActionResponse.model_validate(a) for a in actions]


@router.get("/{action_id}", response_model=ActionResponse)
async def get_action(
    action_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> ActionResponse:
    action_repo = ActionRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    action = await action_repo.get_by_id(action_id)
    return ActionResponse.model_validate(action)


@router.post("/{action_id}/approve", response_model=ActionResponse)
async def approve(
    action_id: uuid.UUID,
    body: ApproveActionRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> ActionResponse:
    _require_approver(ctx)
    try:
        result = await approve_action(
            session,
            tenant_id=ctx.tenant_id,
            project_id=ctx.project_id,
            action_id=action_id,
            approver_id=ctx.user.id,
            reason=body.reason,
            expected_payload_hash=body.expected_payload_hash,
        )
    except ActionNotApprovableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PayloadHashMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ApprovalExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc

    if result.execution_error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=result.execution_error)
    return ActionResponse.model_validate(result.action)


@router.post("/{action_id}/reject", response_model=ActionResponse)
async def reject(
    action_id: uuid.UUID,
    body: RejectActionRequest,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> ActionResponse:
    _require_approver(ctx)
    try:
        action = await reject_action(
            session,
            tenant_id=ctx.tenant_id,
            project_id=ctx.project_id,
            action_id=action_id,
            approver_id=ctx.user.id,
            reason=body.reason,
        )
    except ActionNotApprovableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ActionResponse.model_validate(action)
