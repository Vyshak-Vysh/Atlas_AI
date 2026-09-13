from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership_query
from atlasai_api.schemas.evidence import EvidenceSearchResponse
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_domain.enums import AuditEventType
from atlasai_retrieval import search_evidence

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


@router.get("/search", response_model=EvidenceSearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    top_n: int = Query(default=10, ge=1, le=50),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceSearchResponse:
    results = await search_evidence(
        session, tenant_id=ctx.tenant_id, project_id=ctx.project_id, query_text=q, top_n=top_n
    )

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.EVIDENCE_SEARCHED,
        actor_id=ctx.user.id,
        metadata={"query": q, "result_count": len(results)},
    )
    await session.commit()

    return EvidenceSearchResponse(query=q, results=results)
