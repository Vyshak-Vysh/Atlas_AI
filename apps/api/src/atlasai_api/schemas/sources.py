from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel


class SourceRecordResponse(BaseModel):
    id: uuid.UUID
    external_id: str
    record_type: str
    title: str | None
    canonical_url: str | None
    current_version_id: uuid.UUID | None
    visibility: str
    deleted_at: datetime.datetime | None
    created_at: datetime.datetime
    ingestion_status: str

    model_config = {"from_attributes": True}
