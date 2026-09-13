"""JWT access tokens + opaque, revocable refresh tokens.

Access tokens are short-lived, stateless JWTs (never persisted — validity
is purely a function of signature + `exp`). Refresh tokens are NOT JWTs:
they are random opaque strings whose SHA-256 hash is stored in the
`refresh_tokens` table, so a single row can be revoked (BR-014-style
revocation, applied here to sessions rather than connectors) without
needing a JWT blacklist. The raw refresh token is only ever seen by the
client — the server only ever sees/stores its hash.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from atlasai_security.settings import JWTSettings


class TokenError(Exception):
    pass


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    expires_at: datetime


@dataclass(frozen=True)
class IssuedRefreshToken:
    raw_token: str
    token_hash: str
    expires_at: datetime


def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID | None) -> str:
    settings = JWTSettings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.signing_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = JWTSettings()
    try:
        payload = jwt.decode(token, settings.signing_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError as exc:
        raise TokenError("invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise TokenError("token is not an access token")
    return AccessTokenClaims(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=uuid.UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_refresh_token() -> IssuedRefreshToken:
    settings = JWTSettings()
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    return IssuedRefreshToken(raw_token=raw_token, token_hash=hash_token(raw_token), expires_at=expires_at)
