from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.celery_client import enqueue_ingest_source_version
from atlasai_api.deps import ProjectContext, check_project_membership, get_current_user, get_db_session
from atlasai_api.schemas.documents import DocumentUploadResponse
from atlasai_api.services.upload_service import UnsupportedMimeTypeError, upload_document
from atlasai_connectors.manual_upload.malware_scan import MalwareDetectedError, ScannerUnavailableError
from atlasai_connectors.manual_upload.mime_validation import MimeMismatchError
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_domain.enums import AuditEventType

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload(
    request: Request,
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    visibility: str = Form(default="PROJECT"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    # project_id arrives as multipart form data here, not a path/query
    # parameter, so membership is checked manually rather than via
    # `Depends(require_project_membership*)` — see deps.py's
    # check_project_membership docstring.
    ctx = await check_project_membership(session, project_id=project_id, user=user, request=request)

    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file too large")

    try:
        result = await upload_document(
            session,
            tenant_id=ctx.tenant_id,
            project_id=ctx.project_id,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            data=data,
            visibility=visibility,
        )
    except UnsupportedMimeTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except MimeMismatchError as exc:
        await _audit_rejection(session, ctx, reason=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except MalwareDetectedError as exc:
        await _audit_rejection(session, ctx, reason=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file failed malware scan") from exc
    except ScannerUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="malware scanner unavailable"
        ) from exc

    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.DOCUMENT_UPLOADED,
        actor_id=ctx.user.id,
        target_type="source_record",
        target_id=result.source_record.id,
    )
    await session.commit()

    enqueue_ingest_source_version(
        tenant_id=str(ctx.tenant_id),
        source_record_id=str(result.source_record.id),
        source_version_id=str(result.source_version.id),
    )

    return DocumentUploadResponse(
        source_record_id=result.source_record.id,
        source_version_id=result.source_version.id,
        content_hash=result.source_version.content_hash,
        status="PROCESSING",
    )


async def _audit_rejection(session: AsyncSession, ctx: ProjectContext, *, reason: str) -> None:
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.DOCUMENT_REJECTED, actor_id=ctx.user.id, metadata={"reason": reason}
    )
    await session.commit()
