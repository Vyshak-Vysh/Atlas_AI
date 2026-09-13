from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel


class ActionResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    action_type: str
    payload_json: dict[str, Any]
    status: str
    payload_hash: str
    created_at: datetime.datetime
    executed_at: datetime.datetime | None

    model_config = {"from_attributes": True}


class ApproveActionRequest(BaseModel):
    reason: str | None = None
    expected_payload_hash: str | None = None
    """Optional defense-in-depth check (BD_v2.md §7): if the approver's
    client captured the payload hash when it displayed the action for
    review, it can be echoed back here — a mismatch means the payload
    changed since the approver last saw it, and the approval is refused."""


class RejectActionRequest(BaseModel):
    reason: str | None = None
