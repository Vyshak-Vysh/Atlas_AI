"""Repositories for findings and finding_citations."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import selectinload

from atlasai_db.exceptions import NotFoundError
from atlasai_db.models.findings import Finding, FindingCitation
from atlasai_db.repositories.base import ProjectScopedRepository


class FindingRepository(ProjectScopedRepository[Finding]):
    model = Finding

    async def list_for_project(
        self, *, status: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Finding]:
        query = (
            self._scoped_query()
            .order_by(Finding.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Finding.citations))
        )
        if status is not None:
            query = query.where(Finding.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_citations(self, finding_id: uuid.UUID) -> Finding:
        # Async SQLAlchemy has no implicit lazy-load — Finding.citations
        # must be eagerly loaded here or accessing it later raises
        # MissingGreenlet.
        query = self._scoped_query().where(Finding.id == finding_id).options(selectinload(Finding.citations))
        result = await self.session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(Finding.__name__, finding_id)
        return row

    async def create(
        self,
        *,
        agent_run_id: uuid.UUID,
        status: str,
        summary: str,
        facts: list[Any],
        inferences: list[Any],
        conflicts: list[Any],
        missing_evidence: list[Any],
        confidence: Decimal | float | None,
        requires_human_review: bool,
    ) -> Finding:
        finding = Finding(
            agent_run_id=agent_run_id,
            project_id=self.project_id,
            status=status,
            summary=summary,
            facts=facts,
            inferences=inferences,
            conflicts=conflicts,
            missing_evidence=missing_evidence,
            confidence=confidence,
            requires_human_review=requires_human_review,
        )
        return await self.add(finding)

    async def add_citation(
        self, *, finding_id: uuid.UUID, evidence_chunk_id: uuid.UUID, quote: str,
        citation_label: str | None = None, location_json: dict[str, Any] | None = None,
    ) -> FindingCitation:
        citation = FindingCitation(
            finding_id=finding_id,
            evidence_chunk_id=evidence_chunk_id,
            citation_label=citation_label,
            quote=quote,
            location_json=location_json or {},
        )
        self.session.add(citation)
        await self.session.flush()
        return citation
