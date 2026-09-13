from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    external_account_id: str | None
    scopes: dict[str, Any]
    last_sync_at: datetime.datetime | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class ConnectorProviderInfo(BaseModel):
    """One row per known `ConnectorProvider` enum value, so the frontend can
    render a complete connector gallery — including providers this
    deployment has never connected — without inventing data for the ones
    with no `Connector` row yet."""

    provider: str
    display_name: str
    is_available: bool
    """False for providers with no adapter/OAuth wiring in this deployment
    yet (BR: never present a connector as connectable when it cannot
    actually be authorized)."""
    connector: ConnectorResponse | None = None


class CreateConnectorRequest(BaseModel):
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    provider: str
    external_account_id: str | None = Field(default=None, max_length=250)


class SyncRunResponse(BaseModel):
    id: uuid.UUID
    connector_id: uuid.UUID
    status: str
    cursor_before: str | None
    cursor_after: str | None
    started_at: datetime.datetime
    finished_at: datetime.datetime | None
    items_seen: int
    items_changed: int
    error_json: dict[str, Any] | None

    model_config = {"from_attributes": True}
