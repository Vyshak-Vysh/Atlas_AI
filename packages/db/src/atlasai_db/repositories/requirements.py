"""Repositories for requirements, requirement_evidence, claims, decisions,
delivery_records — all project-scoped."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from atlasai_db.exceptions import NotFoundError
from atlasai_db.models.requirements import (
    Claim,
    Decision,
    DeliveryRecord,
    Requirement,
    RequirementComment,
    RequirementEvidence,
)
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.base import ProjectScopedRepository


class RequirementRepository(ProjectScopedRepository[Requirement]):
    model = Requirement

    async def get_by_key(self, key: str) -> Requirement | None:
        query = self._scoped_query().where(Requirement.key == key)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_phase(self, phase_id: uuid.UUID) -> list[Requirement]:
        query = self._scoped_query().where(Requirement.phase_id == phase_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_project(
        self,
        *,
        status: str | None = None,
        phase_id: uuid.UUID | None = None,
        task_status: str | None = None,
        priority: str | None = None,
        assignee_id: uuid.UUID | None = None,
        sprint_id: uuid.UUID | None = None,
    ) -> list[Requirement]:
        query = self._scoped_query().order_by(Requirement.key)
        if status is not None:
            query = query.where(Requirement.status == status)
        if phase_id is not None:
            query = query.where(Requirement.phase_id == phase_id)
        if task_status is not None:
            query = query.where(Requirement.task_status == task_status)
        if priority is not None:
            query = query.where(Requirement.priority == priority)
        if assignee_id is not None:
            query = query.where(Requirement.assignee_id == assignee_id)
        if sprint_id is not None:
            query = query.where(Requirement.sprint_id == sprint_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_relations(self, requirement_id: uuid.UUID) -> Requirement:
        query = (
            self._scoped_query()
            .where(Requirement.id == requirement_id)
            .options(
                selectinload(Requirement.evidence_links),
                selectinload(Requirement.delivery_records),
            )
        )
        result = await self.session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(Requirement.__name__, requirement_id)
        return row

    async def create(
        self, *, key: str, title: str, status: str, phase_id: uuid.UUID | None = None,
        description: str | None = None, acceptance_criteria: list[Any] | None = None,
        task_status: str = "TO_DO", priority: str = "NORMAL", assignee_id: uuid.UUID | None = None,
        sprint_id: uuid.UUID | None = None, due_date: date | None = None,
    ) -> Requirement:
        requirement = Requirement(
            project_id=self.project_id,
            phase_id=phase_id,
            sprint_id=sprint_id,
            key=key,
            title=title,
            description=description,
            status=status,
            acceptance_criteria=acceptance_criteria or [],
            task_status=task_status,
            priority=priority,
            assignee_id=assignee_id,
            due_date=due_date,
        )
        return await self.add(requirement)

    async def update(self, requirement: Requirement, **fields: Any) -> Requirement:
        """Generic partial update: `fields` should already be the caller's
        `exclude_unset=True` dump, so an explicit `None` (e.g. clearing
        assignee_id/phase_id) is applied, not skipped."""
        for name, value in fields.items():
            setattr(requirement, name, value)
        await self.session.flush()
        # Explicit refresh (not just flush) so the server-side `onupdate`
        # value for `updated_at` is loaded into the object while still
        # inside an awaited call — reading an unloaded attribute later,
        # synchronously, would raise SQLAlchemy's MissingGreenlet error.
        await self.session.refresh(requirement)
        return requirement

    async def delete(self, requirement: Requirement) -> None:
        await self.session.delete(requirement)
        await self.session.flush()


class RequirementCommentRepository:
    """Plain (non project-scoped) repository — comments are always reached
    through an already project-scoped parent Requirement, same pattern as
    RequirementEvidenceRepository below."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, requirement_id: uuid.UUID, author_id: uuid.UUID, body: str) -> RequirementComment:
        comment = RequirementComment(requirement_id=requirement_id, author_id=author_id, body=body)
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_for_requirement(self, requirement_id: uuid.UUID) -> list[tuple[RequirementComment, User]]:
        query = (
            select(RequirementComment, User)
            .join(User, User.id == RequirementComment.author_id)
            .where(RequirementComment.requirement_id == requirement_id)
            .order_by(RequirementComment.created_at)
        )
        result = await self.session.execute(query)
        return [(comment, author) for comment, author in result.all()]

    async def get_by_id(self, comment_id: uuid.UUID) -> RequirementComment:
        query = select(RequirementComment).where(RequirementComment.id == comment_id)
        result = await self.session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(RequirementComment.__name__, comment_id)
        return row

    async def update(self, comment: RequirementComment, *, body: str) -> RequirementComment:
        comment.body = body
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def delete(self, comment: RequirementComment) -> None:
        await self.session.delete(comment)
        await self.session.flush()


class RequirementEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def link(
        self, *, requirement_id: uuid.UUID, evidence_chunk_id: uuid.UUID, relation_type: str,
        confidence: float | None = None, rationale: str | None = None,
    ) -> RequirementEvidence:
        link = RequirementEvidence(
            requirement_id=requirement_id,
            evidence_chunk_id=evidence_chunk_id,
            relation_type=relation_type,
            confidence=confidence,
            rationale=rationale,
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def list_for_requirement(self, requirement_id: uuid.UUID) -> list[RequirementEvidence]:
        result = await self.session.execute(
            select(RequirementEvidence).where(RequirementEvidence.requirement_id == requirement_id)
        )
        return list(result.scalars().all())


class ClaimRepository(ProjectScopedRepository[Claim]):
    model = Claim

    async def create(
        self, *, evidence_chunk_id: uuid.UUID, claim_text: str, claim_type: str, polarity: str,
        extracted_by: str, confidence: float | None = None,
    ) -> Claim:
        claim = Claim(
            project_id=self.project_id,
            evidence_chunk_id=evidence_chunk_id,
            claim_text=claim_text,
            claim_type=claim_type,
            polarity=polarity,
            extracted_by=extracted_by,
            confidence=confidence,
        )
        return await self.add(claim)

    async def list_for_evidence_chunk(self, evidence_chunk_id: uuid.UUID) -> list[Claim]:
        query = self._scoped_query().where(Claim.evidence_chunk_id == evidence_chunk_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class DecisionRepository(ProjectScopedRepository[Decision]):
    model = Decision

    async def create(
        self, *, title: str, decision_text: str, decision_status: str, approved_by: uuid.UUID | None = None,
        approved_at: datetime | None = None, effective_at: datetime | None = None, rationale: str | None = None,
    ) -> Decision:
        decision = Decision(
            project_id=self.project_id,
            title=title,
            decision_text=decision_text,
            decision_status=decision_status,
            approved_by=approved_by,
            approved_at=approved_at,
            effective_at=effective_at,
            rationale=rationale,
        )
        return await self.add(decision)


class DeliveryRecordRepository(ProjectScopedRepository[DeliveryRecord]):
    model = DeliveryRecord

    async def list_for_requirement(self, requirement_id: uuid.UUID) -> list[DeliveryRecord]:
        query = self._scoped_query().where(DeliveryRecord.requirement_id == requirement_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self, *, requirement_id: uuid.UUID, status: str, source_record_id: uuid.UUID | None = None,
        evidence_summary: str | None = None, verified_by: uuid.UUID | None = None,
        verified_at: datetime | None = None, metadata: dict[str, Any] | None = None,
    ) -> DeliveryRecord:
        record = DeliveryRecord(
            project_id=self.project_id,
            requirement_id=requirement_id,
            status=status,
            source_record_id=source_record_id,
            evidence_summary=evidence_summary,
            verified_by=verified_by,
            verified_at=verified_at,
            metadata_=metadata or {},
        )
        return await self.add(record)
