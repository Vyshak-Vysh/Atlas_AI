"""connectors, connector_scopes, sync_runs — docs/ERD_FINAL.md §3."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlasai_db.base import Base, TimestampUpdatedMixin, UUIDPKMixin


class Connector(Base, UUIDPKMixin, TimestampUpdatedMixin):
    __tablename__ = "connectors"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_account_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ACTIVE")
    credential_ref: Mapped[str] = mapped_column(String, nullable=False)
    scopes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    last_sync_at: Mapped[datetime | None] = mapped_column()

    scope_rows: Mapped[list[ConnectorScope]] = relationship(back_populates="connector", cascade="all, delete-orphan")
    sync_runs: Mapped[list[SyncRun]] = relationship(back_populates="connector", cascade="all, delete-orphan")


class ConnectorScope(Base, UUIDPKMixin):
    __tablename__ = "connector_scopes"
    __table_args__ = (
        # Postgres identifiers are capped at 63 bytes — a name built by
        # concatenating all four column names (the naming convention's
        # default) would exceed that, so this one is given explicitly.
        UniqueConstraint(
            "connector_id",
            "project_id",
            "scope_type",
            "scope_external_id",
            name="uq_connector_scopes_identity",
        ),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_external_id: Mapped[str | None] = mapped_column(String)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    connector: Mapped[Connector] = relationship(back_populates="scope_rows")


class SyncRun(Base, UUIDPKMixin):
    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint("finished_at is null or finished_at >= started_at", name="finished_after_started"),
    )

    connector_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False
    )
    cursor_before: Mapped[str | None] = mapped_column(String)
    cursor_after: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column()
    items_seen: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    items_changed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    connector: Mapped[Connector] = relationship(back_populates="sync_runs")
