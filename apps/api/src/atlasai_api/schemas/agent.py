from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel


class CreateAgentRunRequest(BaseModel):
    project_id: uuid.UUID
    question: str


class AgentRunResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    question: str
    status: str
    finding_id: uuid.UUID | None = None
    error: str | None = None
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
