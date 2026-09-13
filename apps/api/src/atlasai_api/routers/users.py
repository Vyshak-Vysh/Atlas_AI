from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import get_current_user, get_db_session
from atlasai_api.schemas.users import MyTenantMembershipResponse, UpdateUserRequest, UserResponse
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.tenancy import MembershipRepository, UserRepository

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateUserRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    updated = await UserRepository(session).update_display_name(user, body.display_name)
    await session.commit()
    return UserResponse.model_validate(updated)


@router.get("/me/tenants", response_model=list[MyTenantMembershipResponse])
async def list_my_tenants(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> list[MyTenantMembershipResponse]:
    rows = await MembershipRepository(session).list_tenant_memberships_for_user(user.id)
    return [
        MyTenantMembershipResponse(
            tenant_id=tenant.id, tenant_name=tenant.name, tenant_slug=tenant.slug, role=member.role
        )
        for member, tenant in rows
    ]
