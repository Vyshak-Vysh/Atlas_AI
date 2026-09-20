from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership_query
from atlasai_api.schemas.findings import FindingCitationResponse, FindingResponse
from atlasai_db.models.findings import Finding
from atlasai_db.repositories.findings import FindingRepository

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


def finding_to_response(finding: Finding) -> FindingResponse:
    """Public (not router-private) so other routers — e.g. the space-level
    findings/report rollups in routers/spaces.py — can reuse the exact same
    Finding -> FindingResponse mapping instead of re-deriving it."""
    return FindingResponse(
        id=finding.id,
        agent_run_id=finding.agent_run_id,
        project_id=finding.project_id,
        status=finding.status,
        summary=finding.summary,
        facts=finding.facts,
        inferences=finding.inferences,
        conflicts=finding.conflicts,
        missing_evidence=finding.missing_evidence,
        confidence=float(finding.confidence) if finding.confidence is not None else None,
        requires_human_review=finding.requires_human_review,
        citations=[
            FindingCitationResponse(
                evidence_chunk_id=c.evidence_chunk_id,
                citation_label=c.citation_label,
                quote=c.quote,
                location=c.location_json,
            )
            for c in finding.citations
        ],
        created_at=finding.created_at,
    )


@router.get("", response_model=list[FindingResponse])
async def list_findings(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[FindingResponse]:
    finding_repo = FindingRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    findings = await finding_repo.list_for_project(status=status_filter, limit=limit, offset=offset)
    return [finding_to_response(f) for f in findings]


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> FindingResponse:
    finding_repo = FindingRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    finding = await finding_repo.get_with_citations(finding_id)
    return finding_to_response(finding)
