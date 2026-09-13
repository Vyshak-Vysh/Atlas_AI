from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel

from atlasai_db.models.audit import AuditEvent


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    event_type: str
    target_type: str | None
    target_id: uuid.UUID | None
    request_id: str | None
    metadata: dict[str, Any]
    created_at: datetime.datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, event: AuditEvent) -> AuditEventResponse:
        return cls(
            id=event.id,
            actor_id=event.actor_id,
            event_type=event.event_type,
            target_type=event.target_type,
            target_id=event.target_id,
            request_id=event.request_id,
            metadata=event.metadata_,
            created_at=event.created_at,
        )
