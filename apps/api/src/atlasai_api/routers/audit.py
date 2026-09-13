from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import check_tenant_membership, get_current_user, get_db_session
from atlasai_api.schemas.audit import AuditEventResponse
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_security import Permission, role_has_permission

router = APIRouter(prefix="/api/v1/audit-events", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse])
async def list_audit_events(
    request: Request,
    tenant_id: uuid.UUID = Query(...),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuditEventResponse]:
    role = await check_tenant_membership(session, tenant_id=tenant_id, user=user, request=request)
    if not role_has_permission(role, Permission.VIEW_AUDIT_LOG):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot view the audit log")

    events = await AuditEventRepository(session, tenant_id=tenant_id).list_recent(limit=limit, offset=offset)
    return [AuditEventResponse.from_model(e) for e in events]
