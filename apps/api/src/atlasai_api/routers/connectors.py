"""Connector management.

Only `MANUAL_UPLOAD` has a real, working adapter in this deployment today
(`packages/connectors/src/atlasai_connectors/manual_upload`) — every other
`ConnectorProvider` enum value (Gmail, Microsoft Graph, Google Drive,
meeting transcripts, PM/Jira, Git/CI) has no OAuth client wiring or sync
adapter yet. Per the frontend's evidence-first rule ("never present a
connector as connectable when it cannot actually be authorized"), this
router reports every provider's real availability rather than pretending
they can all be connected — `is_available=False` providers are shown to the
frontend as "not yet configured for this deployment", not as a working
connect button.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from atlasai_api.deps import (
    ProjectContext,
    check_tenant_membership,
    get_current_user,
    get_db_session,
    require_project_membership_query,
)
from atlasai_api.schemas.connectors import (
    ConnectorProviderInfo,
    ConnectorResponse,
    CreateConnectorRequest,
    SyncRunResponse,
)
from atlasai_db.models.tenancy import User
from atlasai_db.repositories.audit import AuditEventRepository
from atlasai_db.repositories.connectors import ConnectorRepository, ConnectorScopeRepository, SyncRunRepository
from atlasai_domain.enums import AuditEventType, ConnectorProvider, ConnectorStatus, MembershipRole

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

# The single source of truth for "can the frontend actually connect this
# provider right now" — update this set as real adapters ship.
_AVAILABLE_PROVIDERS = {ConnectorProvider.MANUAL_UPLOAD}

_PROVIDER_DISPLAY_NAMES = {
    ConnectorProvider.MANUAL_UPLOAD: "Manual upload",
    ConnectorProvider.GIT_CI_GITHUB: "GitHub / CI",
    ConnectorProvider.GMAIL: "Gmail",
    ConnectorProvider.MSGRAPH: "Microsoft 365 / Outlook",
    ConnectorProvider.GOOGLE_DRIVE: "Google Drive",
    ConnectorProvider.MEETINGS: "Meeting transcripts",
    ConnectorProvider.PM_JIRA: "Jira / PM tools",
}

_PROJECT_CREATOR_ROLES = {MembershipRole.PROJECT_MANAGER, MembershipRole.AI_ENGINEER_ADMIN}


@router.get("", response_model=list[ConnectorProviderInfo])
async def list_connectors(
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[ConnectorProviderInfo]:
    connector_repo = ConnectorRepository(session, tenant_id=ctx.tenant_id)
    connected = await connector_repo.list_for_project(ctx.project_id)
    connected_by_provider = {c.provider: c for c in connected}

    return [
        ConnectorProviderInfo(
            provider=provider.value,
            display_name=_PROVIDER_DISPLAY_NAMES[provider],
            is_available=provider in _AVAILABLE_PROVIDERS,
            connector=ConnectorResponse.model_validate(connected_by_provider[provider.value])
            if provider.value in connected_by_provider
            else None,
        )
        for provider in ConnectorProvider
    ]


@router.post("", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(
    body: CreateConnectorRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConnectorResponse:
    role = await check_tenant_membership(session, tenant_id=body.tenant_id, user=user, request=request)
    if role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage connectors")

    try:
        provider = ConnectorProvider(body.provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid provider") from exc

    if provider not in _AVAILABLE_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{_PROVIDER_DISPLAY_NAMES[provider]} has no OAuth adapter configured in this deployment yet",
        )

    connector_repo = ConnectorRepository(session, tenant_id=body.tenant_id)

    # Idempotency: manual-upload connectors are also lazily created by the
    # first document upload to a project (services/upload_service.py) — if
    # that has already happened, reuse it rather than creating a duplicate
    # Connector row for the same (tenant, project, provider).
    existing = [c for c in await connector_repo.list_for_project(body.project_id) if c.provider == provider.value]
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{_PROVIDER_DISPLAY_NAMES[provider]} is already connected for this project",
        )

    connector = await connector_repo.create(
        provider=provider.value,
        credential_ref="local:manual-upload",
        external_account_id=body.external_account_id,
    )
    await ConnectorScopeRepository(session).add(
        connector_id=connector.id,
        project_id=body.project_id,
        scope_type="project",
        scope_external_id=None,
        scope_json={},
    )
    await AuditEventRepository(session, tenant_id=body.tenant_id).record(
        event_type=AuditEventType.CONNECTOR_CREATED,
        actor_id=user.id,
        target_type="connector",
        target_id=connector.id,
        request_id=request.headers.get("x-request-id"),
        metadata={"provider": provider.value, "project_id": str(body.project_id)},
    )
    await session.commit()
    return ConnectorResponse.model_validate(connector)


@router.get("/{connector_id}/sync-runs", response_model=list[SyncRunResponse])
async def list_sync_runs(
    connector_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> list[SyncRunResponse]:
    connector_repo = ConnectorRepository(session, tenant_id=ctx.tenant_id)
    connectors = await connector_repo.list_for_project(ctx.project_id)
    if not any(c.id == connector_id for c in connectors):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="connector not found")

    runs = await SyncRunRepository(session).list_for_connector(connector_id)
    return [SyncRunResponse.model_validate(r) for r in runs]


@router.delete("/{connector_id}", response_model=ConnectorResponse)
async def revoke_connector(
    connector_id: uuid.UUID,
    request: Request,
    ctx: ProjectContext = Depends(require_project_membership_query),
    session: AsyncSession = Depends(get_db_session),
) -> ConnectorResponse:
    if ctx.role not in _PROJECT_CREATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role cannot manage connectors")

    connector_repo = ConnectorRepository(session, tenant_id=ctx.tenant_id)
    connectors = await connector_repo.list_for_project(ctx.project_id)
    connector = next((c for c in connectors if c.id == connector_id), None)
    if connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="connector not found")

    connector = await connector_repo.set_status(connector, ConnectorStatus.REVOKED.value)
    await AuditEventRepository(session, tenant_id=ctx.tenant_id).record(
        event_type=AuditEventType.CONNECTOR_REVOKED,
        actor_id=ctx.user.id,
        target_type="connector",
        target_id=connector_id,
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()
    return ConnectorResponse.model_validate(connector)
