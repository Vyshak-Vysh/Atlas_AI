"""Manual document upload: validate -> store raw bytes -> create
source_record/source_version -> enqueue ingestion -> audit.

Project association for source_records (project-to-evidence scoping):
docs/ERD_FINAL.md's `source_records` table carries only `tenant_id`, not a
`project_id` — the ERD's intended join path for "which project does this
evidence belong to" is `source_records.connector_id -> connectors ->
connector_scopes.project_id`. This service implements that path for manual
uploads by lazily creating one MANUAL_UPLOAD connector per (tenant,
project) the first time that project receives an upload, then reusing it
on every subsequent upload to the same project — no new tables or columns,
just a documented way of populating the existing ones. packages/retrieval
joins through the same path to scope search results to a project.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_connectors.manual_upload.malware_scan import scan_bytes
from atlasai_connectors.manual_upload.mime_validation import validate_mime_type
from atlasai_connectors.manual_upload.parsers import SUPPORTED_MIME_TYPES
from atlasai_db.models.connectors import Connector, ConnectorScope
from atlasai_db.models.evidence import SourceRecord, SourceVersion
from atlasai_db.object_store import ObjectStoreClient
from atlasai_db.repositories.evidence import SourceRecordRepository, SourceVersionRepository
from atlasai_domain.enums import ConnectorProvider


class UnsupportedMimeTypeError(Exception):
    pass


@dataclass(frozen=True)
class UploadResult:
    source_record: SourceRecord
    source_version: SourceVersion


async def _get_or_create_manual_upload_connector(
    session: AsyncSession, *, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> Connector:
    result = await session.execute(
        select(Connector)
        .join(ConnectorScope, ConnectorScope.connector_id == Connector.id)
        .where(
            Connector.tenant_id == tenant_id,
            Connector.provider == ConnectorProvider.MANUAL_UPLOAD.value,
            ConnectorScope.project_id == project_id,
        )
        .limit(1)
    )
    connector = result.scalar_one_or_none()
    if connector is not None:
        return connector

    connector = Connector(
        tenant_id=tenant_id, provider=ConnectorProvider.MANUAL_UPLOAD.value, credential_ref="manual", status="ACTIVE"
    )
    session.add(connector)
    await session.flush()

    scope = ConnectorScope(
        connector_id=connector.id, project_id=project_id, scope_type="project", scope_external_id=str(project_id)
    )
    session.add(scope)
    await session.flush()
    return connector


async def upload_document(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    visibility: str = "PROJECT",
) -> UploadResult:
    if content_type not in SUPPORTED_MIME_TYPES:
        raise UnsupportedMimeTypeError(f"unsupported content type: {content_type}")

    validate_mime_type(data, content_type)  # raises MimeMismatchError
    scan_bytes(data)  # raises MalwareDetectedError / ScannerUnavailableError

    content_hash = hashlib.sha256(data).hexdigest()

    connector = await _get_or_create_manual_upload_connector(session, tenant_id=tenant_id, project_id=project_id)

    object_store = ObjectStoreClient()
    raw_key = f"{tenant_id}/{project_id}/{content_hash}/original"
    stored = object_store.put_raw(key=raw_key, data=data, content_type=content_type)

    source_repo = SourceRecordRepository(session, tenant_id=tenant_id)
    source_record = await source_repo.create(
        connector_id=connector.id,
        external_id=str(uuid.uuid4()),
        record_type="document",
        title=filename,
        canonical_url=None,
        visibility=visibility,
    )

    version_repo = SourceVersionRepository(session)
    source_version = await version_repo.create(
        source_record_id=source_record.id,
        version_key=content_hash,
        content_hash=content_hash,
        raw_object_uri=stored.uri,
        extracted_text_uri=None,
        metadata={"mime_type": content_type, "filename": filename},
    )

    await session.commit()
    return UploadResult(source_record=source_record, source_version=source_version)
