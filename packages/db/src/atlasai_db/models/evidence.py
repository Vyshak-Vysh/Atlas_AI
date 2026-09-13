"""source_records, source_versions, evidence_chunks — docs/ERD_FINAL.md §3.

`source_records.current_version_id` -> `source_versions.id` and
`source_versions.source_record_id` -> `source_records.id` form a two-table
cycle. `use_alter=True` tells SQLAlchemy (and Alembic autogenerate) to emit
the `current_version_id` FK as a separate `ALTER TABLE ... ADD CONSTRAINT`
after both tables exist, rather than failing to order the CREATE TABLE
statements (ERD_FINAL.md critical integrity rule #1).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlasai_db.base import Base, TimestampMixin, TimestampUpdatedMixin, UUIDPKMixin
from atlasai_db.settings import EMBEDDING_DIMENSION


class SourceRecord(Base, UUIDPKMixin, TimestampUpdatedMixin):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint("connector_id", "external_id", name="uq_source_records_connector_id_external_id"),
        Index("ix_source_records_tenant_type", "tenant_id", "record_type"),
        Index("ix_source_records_connector_external", "connector_id", "external_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("connectors.id", ondelete="SET NULL")
    )
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    record_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    canonical_url: Mapped[str | None] = mapped_column(String)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "source_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_source_records_current_version_id_source_versions",
        ),
    )
    visibility: Mapped[str] = mapped_column(String(30), nullable=False, server_default="PROJECT")
    deleted_at: Mapped[datetime | None] = mapped_column()

    versions: Mapped[list[SourceVersion]] = relationship(
        back_populates="source_record",
        cascade="all, delete-orphan",
        foreign_keys="SourceVersion.source_record_id",
    )
    current_version: Mapped[SourceVersion | None] = relationship(foreign_keys=[current_version_id], viewonly=True)


class SourceVersion(Base, UUIDPKMixin):
    __tablename__ = "source_versions"
    __table_args__ = (
        UniqueConstraint("source_record_id", "version_key", name="uq_source_versions_source_record_id_version_key"),
    )

    source_record_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False
    )
    version_key: Mapped[str] = mapped_column(String, nullable=False)
    authored_at: Mapped[datetime | None] = mapped_column()
    modified_at: Mapped[datetime | None] = mapped_column()
    imported_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)
    meeting_at: Mapped[datetime | None] = mapped_column()
    effective_at: Mapped[datetime | None] = mapped_column()
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_object_uri: Mapped[str | None] = mapped_column(String)
    extracted_text_uri: Mapped[str | None] = mapped_column(String)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    source_record: Mapped[SourceRecord] = relationship(
        back_populates="versions", foreign_keys=[source_record_id]
    )
    chunks: Mapped[list[EvidenceChunk]] = relationship(back_populates="source_version", cascade="all, delete-orphan")


# DESC ordering requires referencing the mapped column object, which only
# exists once the class body above has finished executing — hence these
# two live here rather than in SourceVersion.__table_args__.
Index("ix_source_versions_record_modified", SourceVersion.source_record_id, SourceVersion.modified_at.desc())
Index("ix_source_versions_hash", SourceVersion.content_hash)


class EvidenceChunk(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "evidence_chunks"
    __table_args__ = (
        UniqueConstraint("source_version_id", "chunk_index", name="uq_evidence_chunks_source_version_id_chunk_index"),
        CheckConstraint("token_count is null or token_count >= 0", name="token_count_nonnegative"),
        CheckConstraint(
            "start_ms is null or end_ms is null or end_ms >= start_ms",
            name="end_ms_after_start_ms",
        ),
        Index("ix_evidence_chunks_tenant_version", "tenant_id", "source_version_id"),
        Index("ix_evidence_chunks_search_tsv", "search_tsv", postgresql_using="gin"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[str | None] = mapped_column(String)
    sheet_name: Mapped[str | None] = mapped_column(String)
    cell_range: Mapped[str | None] = mapped_column(String)
    speaker: Mapped[str | None] = mapped_column(String)
    start_ms: Mapped[int | None] = mapped_column(BigInteger)
    end_ms: Mapped[int | None] = mapped_column(BigInteger)
    embedding_model: Mapped[str | None] = mapped_column(String(150))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION))
    search_tsv: Mapped[str | None] = mapped_column(TSVECTOR)
    """Populated by a DB trigger (see infra/migrations versions for
    evidence_chunks) — never written from Python."""
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    deleted_at: Mapped[datetime | None] = mapped_column()

    source_version: Mapped[SourceVersion] = relationship(back_populates="chunks")
