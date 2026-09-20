from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, Field


class CreateSprintRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sprint_number: int
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class SprintResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    sprint_number: int
    start_date: datetime.date | None
    end_date: datetime.date | None
    status: str

    model_config = {"from_attributes": True}


class SprintDetailResponse(BaseModel):
    sprint: SprintResponse
    task_count: int
    done_count: int


class UpdateSprintRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    status: str | None = None
