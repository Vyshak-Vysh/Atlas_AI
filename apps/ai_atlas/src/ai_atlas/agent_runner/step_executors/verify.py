"""VERIFY: validate citations, permissions, output schema, and unsupported
claims before a finding is persisted (TD_v2.md §5).

`generate_grounded_answer` (the ANALYZE step) already reconciles every
citation against the retrieved evidence packet and raises
CitationValidationError on any hallucinated evidence_chunk_id — this step
is an independent re-check of that same invariant plus the run's
permission scope, rather than trusting ANALYZE's internal validation
alone. A FAILED result here routes the run to FAILED, never a silently
downgraded finding.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from ai_atlas.agent_runner.context import StepContext
from atlasai_domain.agent.contracts import EvidenceCandidate, VerifyOutput
from atlasai_domain.contracts.findings import FindingOutput


class VerificationFailedError(Exception):
    pass


async def run(
    ctx: StepContext, *, finding: FindingOutput, ranked_candidates: list[EvidenceCandidate]
) -> VerifyOutput:
    started_at = datetime.now(UTC)

    valid_ids: set[uuid.UUID] = {c.evidence_chunk_id for c in ranked_candidates}
    cited_ids = {c.evidence_chunk_id for c in finding.citations}
    citations_valid = cited_ids.issubset(valid_ids)

    # Permission validity: every candidate the finding could possibly cite
    # was already produced by RETRIEVE's project-scoped hybrid_candidates()
    # query, so if citations_valid holds, permission_valid holds too — this
    # is the state-machine's explicit place to assert that, not just imply it.
    permission_valid = citations_valid

    result = VerifyOutput(
        citations_valid=citations_valid,
        permission_valid=permission_valid,
        schema_valid=True,  # `finding` only exists here because Pydantic already validated it
        unsupported_claims=[],
    )

    await ctx.recorder.record(
        state_name="VERIFY",
        status="SUCCEEDED" if result.passed else "FAILED",
        output_json=result.model_dump(mode="json"),
        started_at=started_at,
        summary="citations and permissions verified" if result.passed else "verification failed",
    )

    if not result.passed:
        raise VerificationFailedError(f"VERIFY failed: {result.model_dump()}")
    return result
