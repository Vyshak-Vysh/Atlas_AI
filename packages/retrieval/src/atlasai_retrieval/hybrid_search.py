"""Hybrid retrieval: Postgres full-text search + pgvector cosine
similarity, merged and deduplicated (TD_v2.md §7 "Candidate generation").

Every query is filtered to a single tenant+project before either search
runs — via the same connector_scopes join path documented in apps/api's
upload_service.py — and excludes tombstoned source_records/evidence_chunks
centrally (ERD_FINAL.md critical integrity rule #7), so a caller cannot
construct a query that skips either check.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.models.connectors import Connector, ConnectorScope
from atlasai_db.models.evidence import EvidenceChunk, SourceRecord, SourceVersion
from atlasai_domain.contracts.evidence import EvidenceCandidate, EvidenceLocation, EvidenceTimestamps


def _project_scoped_base_query(*, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Select[Any]:
    return (
        select(EvidenceChunk, SourceRecord, SourceVersion)
        .join(SourceVersion, SourceVersion.id == EvidenceChunk.source_version_id)
        .join(SourceRecord, SourceRecord.id == SourceVersion.source_record_id)
        .join(Connector, Connector.id == SourceRecord.connector_id)
        .join(ConnectorScope, ConnectorScope.connector_id == Connector.id)
        .where(
            EvidenceChunk.tenant_id == tenant_id,
            EvidenceChunk.deleted_at.is_(None),
            SourceRecord.deleted_at.is_(None),
            ConnectorScope.project_id == project_id,
        )
    )


def _row_to_candidate(
    chunk: EvidenceChunk, source_record: SourceRecord, source_version: SourceVersion
) -> EvidenceCandidate:
    return EvidenceCandidate(
        evidence_chunk_id=chunk.id,
        source_record_id=source_record.id,
        source_version_id=source_version.id,
        content=chunk.content,
        location=EvidenceLocation(
            page_number=chunk.page_number,
            section_path=chunk.section_path,
            sheet_name=chunk.sheet_name,
            cell_range=chunk.cell_range,
            speaker=chunk.speaker,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
        ),
        timestamps=EvidenceTimestamps(
            authored_at=source_version.authored_at,
            modified_at=source_version.modified_at,
            imported_at=source_version.imported_at,
            meeting_at=source_version.meeting_at,
            effective_at=source_version.effective_at,
        ),
        visibility=source_record.visibility,
    )


async def lexical_search(
    session: AsyncSession, *, tenant_id: uuid.UUID, project_id: uuid.UUID, query_text: str, limit: int
) -> dict[uuid.UUID, tuple[EvidenceCandidate, float]]:
    tsquery = func.plainto_tsquery("english", query_text)
    rank = func.ts_rank(EvidenceChunk.search_tsv, tsquery)
    query = (
        _project_scoped_base_query(tenant_id=tenant_id, project_id=project_id)
        .where(EvidenceChunk.search_tsv.op("@@")(tsquery))
        .add_columns(rank.label("rank"))
        .order_by(rank.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    out: dict[uuid.UUID, tuple[EvidenceCandidate, float]] = {}
    for chunk, source_record, source_version, rank_value in result.all():
        out[chunk.id] = (_row_to_candidate(chunk, source_record, source_version), float(rank_value))
    return out


async def vector_search(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    query_embedding: list[float],
    limit: int,
) -> dict[uuid.UUID, tuple[EvidenceCandidate, float]]:
    distance = EvidenceChunk.embedding.cosine_distance(query_embedding)
    query = (
        _project_scoped_base_query(tenant_id=tenant_id, project_id=project_id)
        .where(EvidenceChunk.embedding.is_not(None))
        .add_columns(distance.label("distance"))
        .order_by(distance.asc())
        .limit(limit)
    )
    result = await session.execute(query)
    out: dict[uuid.UUID, tuple[EvidenceCandidate, float]] = {}
    for chunk, source_record, source_version, distance_value in result.all():
        similarity = 1.0 - float(distance_value)  # cosine distance -> similarity, for a score where higher is better
        out[chunk.id] = (_row_to_candidate(chunk, source_record, source_version), similarity)
    return out


async def hybrid_candidates(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    query_text: str,
    query_embedding: list[float],
    limit: int = 40,
) -> list[EvidenceCandidate]:
    """Merge + dedupe lexical and vector candidates by evidence_chunk id
    (TD_v2.md §7 step 6). Reranking is a separate step — see rerank.py."""
    # Sequential, not concurrent: both queries share one AsyncSession, and
    # SQLAlchemy's async session is not safe for concurrent use from
    # multiple coroutines against the same connection.
    lexical = await lexical_search(
        session, tenant_id=tenant_id, project_id=project_id, query_text=query_text, limit=limit
    )
    vector = await vector_search(
        session, tenant_id=tenant_id, project_id=project_id, query_embedding=query_embedding, limit=limit
    )

    merged: dict[uuid.UUID, EvidenceCandidate] = {}
    for chunk_id, (candidate, score) in lexical.items():
        merged[chunk_id] = candidate.model_copy(update={"lexical_score": score})
    for chunk_id, (candidate, score) in vector.items():
        if chunk_id in merged:
            merged[chunk_id] = merged[chunk_id].model_copy(update={"vector_score": score})
        else:
            merged[chunk_id] = candidate.model_copy(update={"vector_score": score})

    return list(merged.values())
