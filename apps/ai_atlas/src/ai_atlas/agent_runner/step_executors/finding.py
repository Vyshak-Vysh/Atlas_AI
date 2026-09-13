"""FINDING: persist the structured assessment (TD_v2.md §5)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_db.models.findings import Finding
from atlasai_db.repositories.findings import FindingRepository
from atlasai_domain.contracts.findings import FindingOutput


async def run(ctx: StepContext, *, finding: FindingOutput) -> Finding:
    started_at = datetime.now(UTC)

    finding_repo = FindingRepository(ctx.session, tenant_id=ctx.tenant_id, project_id=ctx.project_id)
    finding_row = await finding_repo.create(
        agent_run_id=ctx.agent_run.id,
        status=finding.status.value,
        summary=finding.summary,
        facts=finding.facts,
        inferences=finding.inferences,
        conflicts=[c.model_dump(mode="json") for c in finding.contradictions],
        missing_evidence=[m.model_dump(mode="json") for m in finding.missing_evidence],
        confidence=finding.confidence,
        requires_human_review=finding.requires_human_review,
    )
    for citation in finding.citations:
        await finding_repo.add_citation(
            finding_id=finding_row.id,
            evidence_chunk_id=citation.evidence_chunk_id,
            quote=citation.quote,
            citation_label=citation.citation_label,
            location_json=citation.location.model_dump(mode="json"),
        )
    await ctx.session.commit()

    await ctx.recorder.record(
        state_name="FINDING",
        status="SUCCEEDED",
        output_json={"finding_id": str(finding_row.id), "status": finding.status.value},
        started_at=started_at,
        summary=f"finding {finding_row.id} persisted",
    )
    return finding_row
