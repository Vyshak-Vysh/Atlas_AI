"""Additive auth tables — NOT part of docs/ERD_FINAL.md's literal table
catalogue. `ERD_FINAL.md` intentionally has no password/session storage
because it assumes an external IdP; the build decision (see docs/ADR/0007
and 0008) is a built-in email+password provider instead, so these two
tables carry only what that requires, kept fully separate from `users` so
the ERD's own `users` table stays byte-for-byte as specified.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from atlasai_db.base import Base, TimestampMixin, UUIDPKMixin


class LocalCredential(Base):
    """One row per user who authenticates via the built-in password
    provider. A user authenticating solely via a future external OIDC
    provider would have no row here."""

    __tablename__ = "local_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), onupdate=text("now()"), nullable=False
    )


class RefreshToken(Base, UUIDPKMixin, TimestampMixin):
    """Revocable refresh tokens. Only the SHA-256 hash of the token is
    stored — the raw token is never persisted, mirroring how password
    hashes are handled."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
