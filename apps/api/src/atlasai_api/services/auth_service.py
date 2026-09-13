"""Registration, login, refresh, and logout.

Registration creates a brand-new tenant plus its first user as
AI_ENGINEER_ADMIN — BD_v2.md leaves self-serve vs. invite-only
provisioning unspecified, so this build offers self-serve tenant creation
plus explicit member-invite endpoints (see routers/tenants.py,
routers/projects.py) for adding further users to an existing tenant/project.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.models.tenancy import TenantMember
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.auth import LocalCredentialRepository, RefreshTokenRepository
from atlasai_db.repositories.tenancy import MembershipRepository, TenantRepository, UserRepository
from atlasai_domain.enums import AuditEventType, MembershipRole, TenantStatus
from atlasai_security import (
    IssuedRefreshToken,
    TokenError,
    create_access_token,
    hash_password,
    hash_token,
    issue_refresh_token,
    verify_password,
)

_SLUG_SANITIZE = re.compile(r"[^a-z0-9]+")


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    user_id: uuid.UUID
    tenant_id: uuid.UUID


def _slugify(name: str, suffix: str) -> str:
    base = _SLUG_SANITIZE.sub("-", name.lower()).strip("-") or "tenant"
    return f"{base}-{suffix}"[:100]


async def register_tenant_and_owner(
    session: AsyncSession, *, tenant_name: str, email: str, password: str, display_name: str
) -> TokenPair:
    tenant_repo = TenantRepository(session)
    user_repo = UserRepository(session)

    if await user_repo.get_by_email(email) is not None:
        raise AuthError("a user with this email already exists")

    tenant = await tenant_repo.create(name=tenant_name, slug=_slugify(tenant_name, uuid.uuid4().hex[:8]))
    user = await user_repo.create(email=email, display_name=display_name, auth_subject=f"local:{email}")
    await LocalCredentialRepository(session).upsert(user_id=user.id, password_hash=hash_password(password))
    await MembershipRepository(session).add_tenant_member(
        tenant_id=tenant.id, user_id=user.id, role=MembershipRole.AI_ENGINEER_ADMIN
    )

    await AuditEventRepository(session, tenant_id=tenant.id).record(
        event_type=AuditEventType.TENANT_CREATED, actor_id=user.id, target_type="tenant", target_id=tenant.id
    )

    pair = await _issue_pair(session, user_id=user.id, tenant_id=tenant.id)
    await session.commit()
    return pair


async def login(session: AsyncSession, *, email: str, password: str) -> TokenPair:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(email)
    if user is None or user.status != TenantStatus.ACTIVE.value:
        raise AuthError("invalid email or password")

    credential = await LocalCredentialRepository(session).get_for_user(user.id)
    if credential is None or not verify_password(plaintext=password, password_hash=credential.password_hash):
        raise AuthError("invalid email or password")

    # A user may belong to multiple tenants; login resolves to their first
    # tenant membership and the client can switch tenants afterward via a
    # fresh token exchange (not implemented in this pass — single-tenant
    # membership is the common case for this build).
    result = await session.execute(select(TenantMember.tenant_id).where(TenantMember.user_id == user.id).limit(1))
    tenant_id = result.scalar_one_or_none()
    if tenant_id is None:
        raise AuthError("user has no tenant membership")

    pair = await _issue_pair(session, user_id=user.id, tenant_id=tenant_id)
    await session.commit()
    return pair


async def refresh(session: AsyncSession, *, raw_refresh_token: str) -> TokenPair:
    token_repo = RefreshTokenRepository(session)
    token_hash = hash_token(raw_refresh_token)
    stored = await token_repo.get_by_hash(token_hash)
    if stored is None or stored.revoked_at is not None or stored.expires_at < datetime.now(UTC):
        raise TokenError("refresh token is invalid, expired, or revoked")

    await token_repo.revoke(stored)  # rotation: one-time-use refresh tokens

    result = await session.execute(
        select(TenantMember.tenant_id).where(TenantMember.user_id == stored.user_id).limit(1)
    )
    tenant_id = result.scalar_one_or_none()
    if tenant_id is None:
        raise TokenError("user has no tenant membership")

    pair = await _issue_pair(session, user_id=stored.user_id, tenant_id=tenant_id)
    await session.commit()
    return pair


async def switch_tenant(session: AsyncSession, *, user_id: uuid.UUID, tenant_id: uuid.UUID) -> TokenPair:
    """Issues a fresh token pair scoped to a different tenant the caller
    already belongs to — the token exchange the `login()` docstring above
    notes as "not implemented in this pass" for the workspace switcher."""
    role = await MembershipRepository(session).get_tenant_role(tenant_id=tenant_id, user_id=user_id)
    if role is None:
        raise AuthError("not a member of that workspace")

    pair = await _issue_pair(session, user_id=user_id, tenant_id=tenant_id)
    await session.commit()
    return pair


async def logout(session: AsyncSession, *, raw_refresh_token: str) -> None:
    token_repo = RefreshTokenRepository(session)
    stored = await token_repo.get_by_hash(hash_token(raw_refresh_token))
    if stored is not None and stored.revoked_at is None:
        await token_repo.revoke(stored)
        await session.commit()


async def _issue_pair(session: AsyncSession, *, user_id: uuid.UUID, tenant_id: uuid.UUID) -> TokenPair:
    access_token = create_access_token(user_id=user_id, tenant_id=tenant_id)
    issued: IssuedRefreshToken = issue_refresh_token()
    await RefreshTokenRepository(session).create(
        user_id=user_id, token_hash=issued.token_hash, expires_at=issued.expires_at
    )
    return TokenPair(access_token=access_token, refresh_token=issued.raw_token, user_id=user_id, tenant_id=tenant_id)
