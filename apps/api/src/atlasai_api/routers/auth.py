from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import get_current_user, get_db_session
from atlasai_api.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SwitchTenantRequest,
    TokenResponse,
)
from atlasai_api.services import auth_service
from atlasai_api.services.auth_service import AuthError
from atlasai_db.models.tenancy import User
from atlasai_security import TokenError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _to_response(pair: auth_service.TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        user_id=pair.user_id,
        tenant_id=pair.tenant_id,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    try:
        pair = await auth_service.register_tenant_and_owner(
            session, tenant_name=body.tenant_name, email=body.email, password=body.password,
            display_name=body.display_name,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _to_response(pair)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    try:
        pair = await auth_service.login(session, email=body.email, password=body.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _to_response(pair)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    try:
        pair = await auth_service.refresh(session, raw_refresh_token=body.refresh_token)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _to_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, session: AsyncSession = Depends(get_db_session)) -> None:
    await auth_service.logout(session, raw_refresh_token=body.refresh_token)


@router.post("/switch-tenant", response_model=TokenResponse)
async def switch_tenant(
    body: SwitchTenantRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    try:
        pair = await auth_service.switch_tenant(session, user_id=user.id, tenant_id=body.tenant_id)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _to_response(pair)
