"""Project report generation.

Deliberately not agent/LLM-driven — every figure here is a direct
aggregation of already-verified rows (phases, requirements, findings,
sources, actions) computed at request time, so the report itself can never
be a source of fabricated information (ATLASAI_MASTER_SPEC.md's
non-negotiable "the LLM is never the system of record" rule). PDF/print
rendering happens client-side (browser print-to-PDF) — this endpoint's job
is only to assemble the trustworthy data behind it.
"""

from __future__ import annotations

import datetime
import uuid
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership
from atlasai_api.schemas.findings import FindingCitationResponse, FindingResponse
from atlasai_api.schemas.projects import PhaseResponse, ProjectResponse
from atlasai_api.schemas.reports import FindingStatusCount, PhaseProgress, ProjectReportResponse
from atlasai_db.repositories.actions import ActionRepository
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.evidence import SourceRecordRepository
from atlasai_db.repositories.findings import FindingRepository
from atlasai_db.repositories.requirements import RequirementRepository
from atlasai_db.repositories.tenancy import MembershipRepository, PhaseRepository, ProjectRepository
from atlasai_domain.enums import ActionStatus, AuditEventType, RequirementStatus

router = APIRouter(prefix="/api/v1/projects", tags=["reports"])

_RECENT_FINDINGS_LIMIT = 20


@router.get("/{project_id}/report", response_model=ProjectReportResponse)
async def get_project_report(
    ctx: ProjectContext = Depends(require_project_membership),
    session: AsyncSession = Depends(get_db_session),
) -> ProjectReportResponse:
    project = await ProjectRepository(session, tenant_id=ctx.tenant_id).get_by_id(ctx.project_id)

    phase_repo = PhaseRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    phases = await phase_repo.list_all(limit=500)

    requirement_repo = RequirementRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    requirements = await requirement_repo.list_for_project()
    requirements_by_phase: dict[uuid.UUID | None, list[Any]] = {}
    for requirement in requirements:
        requirements_by_phase.setdefault(requirement.phase_id, []).append(requirement)

    delivered_statuses = {RequirementStatus.DELIVERED_VERIFIED.value}
    phase_progress = [
        PhaseProgress(
            phase=PhaseResponse.model_validate(phase),
            requirement_count=len(requirements_by_phase.get(phase.id, [])),
            requirements_delivered=sum(
                1 for r in requirements_by_phase.get(phase.id, []) if r.status in delivered_statuses
            ),
        )
        for phase in sorted(phases, key=lambda p: p.phase_number)
    ]

    source_repo = SourceRecordRepository(session, tenant_id=ctx.tenant_id)
    sources = await source_repo.list_for_project(ctx.project_id, limit=500)

    finding_repo = FindingRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    all_findings = await finding_repo.list_for_project(limit=500)
    status_counts = Counter(f.status for f in all_findings)
    recent_with_citations = [
        await finding_repo.get_with_citations(f.id) for f in all_findings[:_RECENT_FINDINGS_LIMIT]
    ]

    action_repo = ActionRepository(session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    pending_actions = await action_repo.list_for_project(status=ActionStatus.WAITING_APPROVAL.value, limit=500)

    member_count = await MembershipRepository(session).count_project_members(ctx.project_id)

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.REPORT_GENERATED,
        actor_id=ctx.user.id,
        target_type="project",
        target_id=ctx.project_id,
    )
    await session.commit()

    return ProjectReportResponse(
        project=ProjectResponse.model_validate(project),
        generated_at=datetime.datetime.now(datetime.UTC),
        phase_progress=phase_progress,
        total_requirements=len(requirements),
        total_sources=len(sources),
        latest_source_at=max((s.created_at for s in sources), default=None),
        total_findings=len(all_findings),
        findings_by_status=[FindingStatusCount(status=s, count=c) for s, c in status_counts.items()],
        recent_findings=[
            FindingResponse(
                id=f.id,
                agent_run_id=f.agent_run_id,
                project_id=f.project_id,
                status=f.status,
                summary=f.summary,
                facts=f.facts,
                inferences=f.inferences,
                conflicts=f.conflicts,
                missing_evidence=f.missing_evidence,
                confidence=float(f.confidence) if f.confidence is not None else None,
                requires_human_review=f.requires_human_review,
                citations=[
                    FindingCitationResponse(
                        evidence_chunk_id=c.evidence_chunk_id,
                        citation_label=c.citation_label,
                        quote=c.quote,
                        location=c.location_json,
                    )
                    for c in f.citations
                ],
                created_at=f.created_at,
            )
            for f in recent_with_citations
        ],
        pending_approvals=len(pending_actions),
        member_count=member_count,
    )
