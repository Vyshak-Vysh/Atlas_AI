"""requirements, requirement_evidence, claims, decisions, delivery_records —
docs/ERD_FINAL.md §3."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlasai_db.base import Base, TimestampUpdatedMixin, UUIDPKMixin


class Requirement(Base, UUIDPKMixin, TimestampUpdatedMixin):
    __tablename__ = "requirements"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_requirements_project_id_key"),
        Index("ix_requirements_project_status", "project_id", "status"),
        Index("ix_requirements_phase", "phase_id"),
        Index("ix_requirements_project_task_status", "project_id", "task_status"),
        Index("ix_requirements_project_priority", "project_id", "priority"),
        Index("ix_requirements_assignee", "assignee_id"),
        Index("ix_requirements_sprint", "sprint_id"),
        Index("ix_requirements_project_sprint", "project_id", "sprint_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    phase_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("phases.id", ondelete="SET NULL")
    )
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sprints.id", ondelete="SET NULL")
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    acceptance_criteria: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    # Day-to-day task-management fields — see atlasai_domain.enums.TaskStatus/
    # TaskPriority for why these are a separate axis from `status` above.
    task_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="TO_DO")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, server_default="NORMAL")
    due_date: Mapped[date | None] = mapped_column(Date)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    evidence_links: Mapped[list[RequirementEvidence]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan"
    )
    delivery_records: Mapped[list[DeliveryRecord]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan"
    )
    comments: Mapped[list[RequirementComment]] = relationship(
        back_populates="requirement", cascade="all, delete-orphan", order_by="RequirementComment.created_at"
    )


class RequirementEvidence(Base):
    __tablename__ = "requirement_evidence"
    __table_args__ = (
        CheckConstraint(
            "confidence is null or confidence between 0 and 1", name="confidence_range"
        ),
    )

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), primary_key=True
    )
    evidence_chunk_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("evidence_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    relation_type: Mapped[str] = mapped_column(String(30), primary_key=True, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    rationale: Mapped[str | None] = mapped_column()

    requirement: Mapped[Requirement] = relationship(back_populates="evidence_links")


class RequirementComment(Base, UUIDPKMixin, TimestampUpdatedMixin):
    """Collaboration thread on a requirement/task. Child-of-scoped-parent
    (no project_id/tenant_id of its own) — always reached through an
    already project-scoped `Requirement`, same category as
    `RequirementEvidence` (see repositories/base.py's module docstring)."""

    __tablename__ = "requirement_comments"
    __table_args__ = (Index("ix_requirement_comments_requirement_created", "requirement_id", "created_at"),)

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    body: Mapped[str] = mapped_column(nullable=False)

    requirement: Mapped[Requirement] = relationship(back_populates="comments")


class Claim(Base, UUIDPKMixin):
    __tablename__ = "claims"
    __table_args__ = (CheckConstraint("confidence is null or confidence between 0 and 1", name="confidence_range"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    evidence_chunk_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("evidence_chunks.id", ondelete="RESTRICT"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(nullable=False)
    claim_type: Mapped[str] = mapped_column(String(40), nullable=False)
    polarity: Mapped[str] = mapped_column(String(20), nullable=False)
    extracted_by: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)


class Decision(Base, UUIDPKMixin):
    __tablename__ = "decisions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    decision_text: Mapped[str] = mapped_column(nullable=False)
    decision_status: Mapped[str] = mapped_column(String(30), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_at: Mapped[datetime | None] = mapped_column()
    effective_at: Mapped[datetime | None] = mapped_column()
    rationale: Mapped[str | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)


class DeliveryRecord(Base, UUIDPKMixin):
    __tablename__ = "delivery_records"

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False
    )
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_summary: Mapped[str | None] = mapped_column()
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    verified_at: Mapped[datetime | None] = mapped_column()
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    requirement: Mapped[Requirement] = relationship(back_populates="delivery_records")
