"""Repositories for the additive local_credentials/refresh_tokens tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.models.auth import LocalCredential, RefreshToken


class LocalCredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_user(self, user_id: uuid.UUID) -> LocalCredential | None:
        return await self.session.get(LocalCredential, user_id)

    async def upsert(self, *, user_id: uuid.UUID, password_hash: str) -> LocalCredential:
        existing = await self.get_for_user(user_id)
        if existing is not None:
            existing.password_hash = password_hash
            await self.session.flush()
            return existing
        credential = LocalCredential(user_id=user_id, password_hash=password_hash)
        self.session.add(credential)
        await self.session.flush()
        return credential


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> RefreshToken:
        token.revoked_at = datetime.now(UTC)
        await self.session.flush()
        return token

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )
        rows = list(result.scalars().all())
        now = datetime.now(UTC)
        for row in rows:
            row.revoked_at = now
        await self.session.flush()
        return len(rows)
