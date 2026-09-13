from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import TenantContext, get_db_session, require_tenant_membership
from atlasai_api.schemas.tenants import (
    AddTenantMemberRequest,
    TenantMemberDetailResponse,
    TenantMemberResponse,
    TenantResponse,
    UpdateMemberRoleRequest,
)
from atlasai_db.exceptions import NotFoundError
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.tenancy import MembershipRepository, TenantRepository, UserRepository
from atlasai_domain.enums import AuditEventType, MembershipRole

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


def _require_admin(ctx: TenantContext) -> None:
    if ctx.role != MembershipRole.AI_ENGINEER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only AI_ENGINEER_ADMIN can manage members")


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    ctx: TenantContext = Depends(require_tenant_membership), session: AsyncSession = Depends(get_db_session)
) -> TenantResponse:
    try:
        tenant = await TenantRepository(session).get_by_id(ctx.tenant_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found") from exc
    return TenantResponse.model_validate(tenant)


@router.post("/{tenant_id}/members", response_model=TenantMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_tenant_member(
    body: AddTenantMemberRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_membership),
    session: AsyncSession = Depends(get_db_session),
) -> TenantMemberResponse:
    _require_admin(ctx)

    try:
        role = MembershipRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid role") from exc

    target_user = await UserRepository(session).get_by_email(body.email)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no user with that email")

    member = await MembershipRepository(session).add_tenant_member(
        tenant_id=ctx.tenant_id, user_id=target_user.id, role=role.value
    )
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.TENANT_MEMBER_ADDED,
        actor_id=ctx.user.id,
        target_type="user",
        target_id=target_user.id,
        request_id=request.headers.get("x-request-id"),
        metadata={"role": role.value},
    )
    await session.commit()
    return TenantMemberResponse(tenant_id=member.tenant_id, user_id=member.user_id, role=member.role)


@router.get("/{tenant_id}/members", response_model=list[TenantMemberDetailResponse])
async def list_tenant_members(
    ctx: TenantContext = Depends(require_tenant_membership), session: AsyncSession = Depends(get_db_session)
) -> list[TenantMemberDetailResponse]:
    rows = await MembershipRepository(session).list_tenant_members(ctx.tenant_id)
    return [
        TenantMemberDetailResponse(
            tenant_id=member.tenant_id,
            user_id=member.user_id,
            email=str(user.email),
            display_name=user.display_name,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, user in rows
    ]


@router.patch("/{tenant_id}/members/{user_id}", response_model=TenantMemberResponse)
async def update_tenant_member_role(
    user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_membership),
    session: AsyncSession = Depends(get_db_session),
) -> TenantMemberResponse:
    _require_admin(ctx)
    try:
        role = MembershipRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid role") from exc

    member = await MembershipRepository(session).update_tenant_member_role(
        tenant_id=ctx.tenant_id, user_id=user_id, role=role.value
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.MEMBER_ROLE_UPDATED,
        actor_id=ctx.user.id,
        target_type="user",
        target_id=user_id,
        request_id=request.headers.get("x-request-id"),
        metadata={"role": role.value, "scope": "tenant"},
    )
    await session.commit()
    return TenantMemberResponse(tenant_id=member.tenant_id, user_id=member.user_id, role=member.role)


@router.delete("/{tenant_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tenant_member(
    user_id: uuid.UUID,
    request: Request,
    ctx: TenantContext = Depends(require_tenant_membership),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    _require_admin(ctx)
    if user_id == ctx.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cannot remove your own membership")

    removed = await MembershipRepository(session).remove_tenant_member(tenant_id=ctx.tenant_id, user_id=user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.MEMBER_REMOVED,
        actor_id=ctx.user.id,
        target_type="user",
        target_id=user_id,
        request_id=request.headers.get("x-request-id"),
        metadata={"scope": "tenant"},
    )
    await session.commit()
