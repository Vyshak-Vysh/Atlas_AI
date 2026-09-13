from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import ProjectContext, get_db_session, require_project_membership_query
from atlasai_api.schemas.sources import SourceRecordResponse
from atlasai_api.services.source_service import delete_source, ingestion_status
from atlasai_db.models.evidence import SourceRecord
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.connectors import is_connector_scoped_to_project
from atlasai_db.repositories.evidence import SourceRecordRepository
from atlasai_domain.enums import AuditEventType

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


async def _get_authorized_source(session: AsyncSession, ctx: ProjectContext, source_id: uuid.UUID) -> SourceRecord:
    source_repo = SourceRecordRepository(session, tenant_id=ctx.tenant_id)
    source_record = await source_repo.get_by_id_including_deleted(source_id)
    is_scoped = await is_connector_scoped_to_project(
        session, connector_id=source_record.connector_id, project_id=ctx.project_id
    )
    if not is_scoped:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="source not found")
    return source_record


@router.get("", response_model=list[SourceRecordResponse])
async def list_sources(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[SourceRecordResponse]:
    source_repo = SourceRecordRepository(session, tenant_id=ctx.tenant_id)
    records = await source_repo.list_for_project(ctx.project_id, limit=limit, offset=offset)
    return [
        SourceRecordResponse(
            id=r.id,
            external_id=r.external_id,
            record_type=r.record_type,
            title=r.title,
            canonical_url=r.canonical_url,
            current_version_id=r.current_version_id,
            visibility=r.visibility,
            deleted_at=r.deleted_at,
            created_at=r.created_at,
            ingestion_status=ingestion_status(r),
        )
        for r in records
    ]


@router.get("/{source_id}", response_model=SourceRecordResponse)
async def get_source(
    source_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> SourceRecordResponse:
    source_record = await _get_authorized_source(session, ctx, source_id)
    return SourceRecordResponse(
        id=source_record.id,
        external_id=source_record.external_id,
        record_type=source_record.record_type,
        title=source_record.title,
        canonical_url=source_record.canonical_url,
        current_version_id=source_record.current_version_id,
        visibility=source_record.visibility,
        deleted_at=source_record.deleted_at,
        created_at=source_record.created_at,
        ingestion_status=ingestion_status(source_record),
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source_endpoint(
    source_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await _get_authorized_source(session, ctx, source_id)  # 404s before anything is mutated if unauthorized
    await delete_source(session, tenant_id=ctx.tenant_id, source_record_id=source_id)
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.SOURCE_DELETED, actor_id=ctx.user.id, target_type="source_record", target_id=source_id
    )
    await session.commit()
