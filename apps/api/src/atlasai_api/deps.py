"""Shared FastAPI dependencies: DB session, authenticated user, and
tenant/project authorization context.

Every tenant/project-scoped endpoint depends on `TenantContext` or
`ProjectContext` (never constructs a repository from raw path parameters
directly) so authorization happens in exactly one place per request, before
any repository call (ERD_FINAL.md critical integrity rule #8).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.engine import get_async_sessionmaker
from atlasai_db.exceptions import NotFoundError
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.tenancy import MembershipRepository, UserRepository, resolve_tenant_id_for_project
from atlasai_domain.enums import AuditEventType, MembershipRole
from atlasai_security import AccessTokenClaims, Permission, TokenError, decode_access_token, role_has_permission

bearer_scheme = HTTPBearer(auto_error=True)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        claims: AccessTokenClaims = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token") from exc

    try:
        user = await UserRepository(session).get_by_id(claims.user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found") from exc

    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user is not active")
    return user


async def _audit_denied_access(
    session: AsyncSession, *, tenant_id: uuid.UUID, actor_id: uuid.UUID, target_type: str, target_id: uuid.UUID,
    request: Request,
) -> None:
    await AuditEventRepository(session, tenant_id=tenant_id).record(
        event_type=AuditEventType.ACCESS_DENIED,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()


@dataclass(frozen=True)
class TenantContext:
    user: User
    tenant_id: uuid.UUID
    role: MembershipRole


async def check_tenant_membership(
    session: AsyncSession, *, tenant_id: uuid.UUID, user: User, request: Request | None = None
) -> MembershipRole:
    """Reusable outside the FastAPI dependency graph — e.g. `POST
    /api/v1/projects`, which takes tenant_id from the request body rather
    than a path parameter, so it cannot use `require_tenant_membership`
    directly as a `Depends(...)`."""
    role = await MembershipRepository(session).get_tenant_role(tenant_id=tenant_id, user_id=user.id)
    if role is None:
        if request is not None:
            await _audit_denied_access(
                session, tenant_id=tenant_id, actor_id=user.id, target_type="tenant", target_id=tenant_id,
                request=request,
            )
        # 404, not 403 — existence of a tenant a caller cannot see is not revealed.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    return MembershipRole(role)


async def require_tenant_membership(
    tenant_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    role = await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    return TenantContext(user=user, tenant_id=tenant_id, role=role)


@dataclass(frozen=True)
class ProjectContext:
    user: User
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    role: MembershipRole


async def check_project_membership(
    session: AsyncSession, *, project_id: uuid.UUID, user: User, request: Request | None = None
) -> ProjectContext:
    """Reusable outside the FastAPI dependency graph — for endpoints where
    project_id arrives as multipart form data (`POST
    /api/v1/documents/upload`) rather than a path or query parameter, so
    they cannot use `require_project_membership`/`require_project_membership_query`
    directly as a `Depends(...)`."""
    tenant_id = await resolve_tenant_id_for_project(session, project_id)
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")

    role = await MembershipRepository(session).get_project_role(project_id=project_id, user_id=user.id)
    if role is None:
        if request is not None:
            await _audit_denied_access(
                session, tenant_id=tenant_id, actor_id=user.id, target_type="project", target_id=project_id,
                request=request,
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return ProjectContext(user=user, tenant_id=tenant_id, project_id=project_id, role=MembershipRole(role))


async def require_project_membership(
    project_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectContext:
    """`project_id` is bound from a URL PATH parameter — use on routes
    shaped like `/projects/{project_id}/...`."""
    return await check_project_membership(session, project_id=project_id, user=user, request=request)


async def require_project_membership_query(
    request: Request,
    project_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectContext:
    """`project_id` is bound from a QUERY parameter (`?project_id=...`) —
    use on routes that aren't nested under `/projects/{project_id}`, such
    as `GET /api/v1/evidence/search`."""
    return await check_project_membership(session, project_id=project_id, user=user, request=request)


def require_permission(permission: Permission) -> Callable[[ProjectContext], Coroutine[Any, Any, ProjectContext]]:
    """Dependency factory: `Depends(require_permission(Permission.APPROVE_ACTION))`
    layered on top of `ProjectContext`/`TenantContext` — raises 403 (not 404;
    the caller is a confirmed member at this point, just lacking a capability)."""

    async def _check(ctx: ProjectContext = Depends(require_project_membership)) -> ProjectContext:
        if not role_has_permission(ctx.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"missing permission: {permission}")
        return ctx

    return _check
