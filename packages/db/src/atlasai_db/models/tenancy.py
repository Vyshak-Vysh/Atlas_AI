"""tenants, users, tenant_members, spaces, projects, project_members, phases,
sprints — docs/ERD_FINAL.md §3."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlasai_db.base import Base, TimestampMixin, TimestampUpdatedMixin, UUIDPKMixin


class Tenant(Base, UUIDPKMixin, TimestampUpdatedMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ACTIVE")

    members: Mapped[list[TenantMember]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    projects: Mapped[list[Project]] = relationship(back_populates="tenant")


class User(Base, UUIDPKMixin, TimestampUpdatedMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ACTIVE")


class TenantMember(Base, TimestampMixin):
    __tablename__ = "tenant_members"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Space(Base, UUIDPKMixin, TimestampUpdatedMixin):
    __tablename__ = "spaces"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_spaces_tenant_id_name"),
        Index("ix_spaces_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    color: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ACTIVE")

    tenant: Mapped[Tenant] = relationship()
    projects: Mapped[list[Project]] = relationship(back_populates="space")


class Project(Base, UUIDPKMixin, TimestampUpdatedMixin):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_projects_tenant_id_code"),
        Index("ix_projects_tenant_status", "tenant_id", "status"),
        Index("ix_projects_space_status", "space_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    space_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(250))
    code: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ACTIVE")
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, server_default="UTC")

    tenant: Mapped[Tenant] = relationship(back_populates="projects")
    space: Mapped[Space | None] = relationship(back_populates="projects")
    members: Mapped[list[ProjectMember]] = relationship(back_populates="project", cascade="all, delete-orphan")
    phases: Mapped[list[Phase]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sprints: Mapped[list[Sprint]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base, TimestampMixin):
    __tablename__ = "project_members"
    __table_args__ = (Index("ix_project_members_user_project", "user_id", "project_id"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Phase(Base, UUIDPKMixin):
    __tablename__ = "phases"
    __table_args__ = (
        CheckConstraint(
            "end_date is null or start_date is null or end_date >= start_date",
            name="end_date_after_start_date",
        ),
        UniqueConstraint("project_id", "phase_number", name="uq_phases_project_id_phase_number"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phase_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    project: Mapped[Project] = relationship(back_populates="phases")


class Sprint(Base, UUIDPKMixin):
    __tablename__ = "sprints"
    __table_args__ = (
        CheckConstraint(
            "end_date is null or start_date is null or end_date >= start_date",
            name="end_date_after_start_date",
        ),
        UniqueConstraint("project_id", "sprint_number", name="uq_sprints_project_id_sprint_number"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sprint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"), nullable=False)

    project: Mapped[Project] = relationship(back_populates="sprints")
