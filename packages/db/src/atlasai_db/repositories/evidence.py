"""Repositories for source_records, source_versions, evidence_chunks.

Hybrid-search query construction (full-text + pgvector) lives in
packages/retrieval, not here — this module only provides the CRUD/lookup
primitives retrieval and ingestion build on, plus the centrally-enforced
tombstone exclusion (ERD_FINAL.md critical integrity rule #7: "Revoked or
deleted source content must be excluded from retrieval").
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_db.exceptions import NotFoundError
from atlasai_db.models.evidence import EvidenceChunk, SourceRecord, SourceVersion
from atlasai_db.repositories.base import TenantScopedRepository


class SourceRecordRepository(TenantScopedRepository[SourceRecord]):
    model = SourceRecord

    def _scoped_query(self) -> Select[tuple[SourceRecord]]:
        # Tombstoned source records are excluded by default everywhere;
        # callers that explicitly need them (e.g. an admin restore view)
        # use get_by_id_including_deleted instead.
        return super()._scoped_query().where(SourceRecord.deleted_at.is_(None))

    async def get_by_id_including_deleted(self, id_: uuid.UUID) -> SourceRecord:
        query = super()._scoped_query().where(SourceRecord.id == id_)
        result = await self.session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(SourceRecord.__name__, id_)
        return row

    async def get_by_external_id(self, *, connector_id: uuid.UUID | None, external_id: str) -> SourceRecord | None:
        query = self._scoped_query().where(
            SourceRecord.connector_id == connector_id, SourceRecord.external_id == external_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        connector_id: uuid.UUID | None,
        external_id: str,
        record_type: str,
        title: str | None,
        canonical_url: str | None,
        visibility: str = "PROJECT",
    ) -> SourceRecord:
        record = SourceRecord(
            tenant_id=self.tenant_id,
            connector_id=connector_id,
            external_id=external_id,
            record_type=record_type,
            title=title,
            canonical_url=canonical_url,
            visibility=visibility,
        )
        return await self.add(record)

    async def soft_delete(self, record: SourceRecord) -> SourceRecord:
        record.deleted_at = datetime.now(UTC)
        await self.session.flush()
        return record

    async def list_for_project(
        self, project_id: uuid.UUID, *, limit: int = 100, offset: int = 0
    ) -> list[SourceRecord]:
        """Sources have no direct `project_id` column — reachable only
        through their connector's scope(s), same join path as
        `is_connector_scoped_to_project` in repositories/connectors.py."""
        from atlasai_db.models.connectors import Connector, ConnectorScope

        query = (
            self._scoped_query()
            .join(Connector, Connector.id == SourceRecord.connector_id)
            .join(ConnectorScope, ConnectorScope.connector_id == Connector.id)
            .where(ConnectorScope.project_id == project_id)
            .order_by(SourceRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class SourceVersionRepository:
    """Reached through an already tenant-scoped SourceRecord."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_version_key(self, *, source_record_id: uuid.UUID, version_key: str) -> SourceVersion | None:
        result = await self.session.execute(
            select(SourceVersion).where(
                SourceVersion.source_record_id == source_record_id, SourceVersion.version_key == version_key
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        source_record_id: uuid.UUID,
        version_key: str,
        content_hash: str,
        raw_object_uri: str | None,
        extracted_text_uri: str | None,
        authored_at: datetime | None = None,
        modified_at: datetime | None = None,
        meeting_at: datetime | None = None,
        effective_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SourceVersion:
        version = SourceVersion(
            source_record_id=source_record_id,
            version_key=version_key,
            content_hash=content_hash,
            raw_object_uri=raw_object_uri,
            extracted_text_uri=extracted_text_uri,
            authored_at=authored_at,
            modified_at=modified_at,
            meeting_at=meeting_at,
            effective_at=effective_at,
            metadata_=metadata or {},
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def list_for_source_record(self, source_record_id: uuid.UUID) -> list[SourceVersion]:
        result = await self.session.execute(
            select(SourceVersion)
            .where(SourceVersion.source_record_id == source_record_id)
            .order_by(SourceVersion.created_at.desc())
        )
        return list(result.scalars().all())


class EvidenceChunkRepository(TenantScopedRepository[EvidenceChunk]):
    model = EvidenceChunk

    def _scoped_query(self) -> Select[tuple[EvidenceChunk]]:
        return super()._scoped_query().where(EvidenceChunk.deleted_at.is_(None))

    async def bulk_create(self, chunks: list[EvidenceChunk]) -> list[EvidenceChunk]:
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def get_many_by_ids(self, ids: list[uuid.UUID]) -> list[EvidenceChunk]:
        query = self._scoped_query().where(EvidenceChunk.id.in_(ids))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def soft_delete_for_source_version(self, source_version_id: uuid.UUID) -> int:
        query = self._scoped_query().where(EvidenceChunk.source_version_id == source_version_id)
        result = await self.session.execute(query)
        rows = list(result.scalars().all())
        now = datetime.now(UTC)
        for row in rows:
            row.deleted_at = now
        await self.session.flush()
        return len(rows)
