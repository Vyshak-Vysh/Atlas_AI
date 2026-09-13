"""Source record lookup and deletion.

Deletion propagates the tombstone to every evidence_chunk across every
version of the source (ERD_FINAL.md critical integrity rule #7: revoked
or deleted content must be excluded from retrieval) — soft-deleting only
the source_record row itself would leave its chunks fully searchable.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.models.evidence import SourceRecord
from atlasai_db.repositories.evidence import EvidenceChunkRepository, SourceRecordRepository, SourceVersionRepository


def ingestion_status(source_record: SourceRecord) -> str:
    return "READY" if source_record.current_version_id is not None else "PROCESSING"


async def delete_source(session: AsyncSession, *, tenant_id: uuid.UUID, source_record_id: uuid.UUID) -> SourceRecord:
    source_repo = SourceRecordRepository(session, tenant_id=tenant_id)
    version_repo = SourceVersionRepository(session)
    chunk_repo = EvidenceChunkRepository(session, tenant_id=tenant_id)

    source_record = await source_repo.get_by_id(source_record_id)
    versions = await version_repo.list_for_source_record(source_record_id)
    for version in versions:
        await chunk_repo.soft_delete_for_source_version(version.id)

    await source_repo.soft_delete(source_record)
    await session.commit()
    return source_record
