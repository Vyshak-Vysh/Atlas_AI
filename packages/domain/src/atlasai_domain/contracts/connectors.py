"""Shared types for the Connector protocol (TD_v2.md §3 / ATLASAI_MASTER_SPEC.md §8).

`packages/connectors/protocol.py` defines the `Connector` Protocol itself and
re-exports these types as the single source of truth, per the implementation
plan — this module has zero dependency on any provider SDK.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from atlasai_domain.enums import ConnectorProvider


class AuthorizationRequest(BaseModel):
    tenant_id: UUID
    provider: ConnectorProvider
    requested_by_user_id: UUID
    redirect_uri: str | None = None
    requested_scopes: list[str] = Field(default_factory=list)


class AuthorizationResult(BaseModel):
    provider: ConnectorProvider
    external_account_id: str
    credential_ref: str
    granted_scopes: list[str] = Field(default_factory=list)
    authorize_url: str | None = None
    """Set instead of credential_ref when the flow requires a browser
    redirect the caller must complete before authorization finishes."""


class AccountRef(BaseModel):
    connector_id: UUID
    external_account_id: str
    credential_ref: str


class ScopeItem(BaseModel):
    """One unit a connector can be scoped to sync (a mailbox, a Drive
    folder, a Jira project, a GitHub repo, ...)."""

    scope_type: str
    scope_external_id: str
    display_name: str
    scope_json: dict[str, Any] = Field(default_factory=dict)


class ExternalItem(BaseModel):
    """A single raw item fetched from a provider, pre-normalization."""

    external_id: str
    record_type: str
    raw_payload: dict[str, Any]
    canonical_url: str | None = None
    authored_at: datetime | None = None
    modified_at: datetime | None = None
    meeting_at: datetime | None = None


class NormalizedSource(BaseModel):
    """The provider-agnostic shape every connector's `normalize()` produces,
    ready to upsert as a source_record + source_version."""

    external_id: str
    record_type: str
    title: str | None = None
    canonical_url: str | None = None
    version_key: str
    authored_at: datetime | None = None
    modified_at: datetime | None = None
    meeting_at: datetime | None = None
    effective_at: datetime | None = None
    extracted_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SyncPage(BaseModel):
    items: list[ExternalItem]
    next_cursor: str | None = None
    has_more: bool = False


class HealthResult(BaseModel):
    healthy: bool
    detail: str | None = None
    checked_at: datetime
