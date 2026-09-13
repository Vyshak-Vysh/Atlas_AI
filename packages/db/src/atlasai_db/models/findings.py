"""findings, finding_citations — docs/ERD_FINAL.md §3."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlasai_db.base import Base, TimestampMixin, UUIDPKMixin


class Finding(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "findings"
    __table_args__ = (CheckConstraint("confidence is null or confidence between 0 and 1", name="confidence_range"),)

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(nullable=False)
    facts: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    inferences: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    conflicts: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    missing_evidence: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    citations: Mapped[list[FindingCitation]] = relationship(back_populates="finding", cascade="all, delete-orphan")


Index("ix_findings_project_created", Finding.project_id, Finding.created_at.desc())


class FindingCitation(Base):
    __tablename__ = "finding_citations"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_chunk_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("evidence_chunks.id", ondelete="RESTRICT"), primary_key=True
    )
    citation_label: Mapped[str | None] = mapped_column(String(50))
    quote: Mapped[str] = mapped_column(nullable=False)
    location_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    finding: Mapped[Finding] = relationship(back_populates="citations")
