"""Declarative base, naming convention, and shared column mixins.

All UUID primary keys use ``server_default=text("gen_random_uuid()")`` (the
pgcrypto extension) rather than a Python-side default, so the database
remains the single source of truth for identity generation even if a row is
inserted outside the ORM (e.g. a raw SQL migration backfill).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Fixed naming convention so Alembic autogenerate produces stable,
# predictable constraint/index names across every migration.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # docs/ERD_FINAL.md §1: "All timestamps use timestamptz and are stored
    # in UTC." Mapping this once here means every `Mapped[datetime]` column
    # in every model gets `TIMESTAMP WITH TIME ZONE` automatically — no
    # model needs to (or should) pass `DateTime(timezone=True)` itself.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)


class TimestampUpdatedMixin(TimestampMixin):
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), onupdate=text("now()"), nullable=False
    )
