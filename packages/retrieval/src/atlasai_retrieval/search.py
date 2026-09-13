"""Top-level retrieval orchestration: normalize -> embed -> hybrid
candidates -> rerank -> evidence packet (TD_v2.md §7). This is what both
`GET /api/v1/evidence/search` (apps/api) and the agent's RETRIEVE/RERANK
steps (apps/ai_atlas/agent_runner, once built) call — one implementation,
not duplicated between the interactive and agentic paths.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_domain.contracts.evidence import EvidenceCandidate
from atlasai_retrieval.embedder_client import EmbedderClient
from atlasai_retrieval.hybrid_search import hybrid_candidates
from atlasai_retrieval.rerank import rerank


async def search_evidence(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    query_text: str,
    candidate_limit: int = 40,
    top_n: int = 10,
) -> list[EvidenceCandidate]:
    normalized_query = query_text.strip()
    if not normalized_query:
        return []

    embedder = EmbedderClient()
    try:
        query_embedding = await embedder.embed_query(normalized_query)
    finally:
        await embedder.aclose()

    candidates = await hybrid_candidates(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        query_text=normalized_query,
        query_embedding=query_embedding,
        limit=candidate_limit,
    )
    return rerank(candidates, query_text=normalized_query, top_n=top_n)
