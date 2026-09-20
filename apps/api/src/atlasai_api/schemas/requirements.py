from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, Field


class CreateRequirementRequest(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    status: str
    phase_id: uuid.UUID | None = None
    sprint_id: uuid.UUID | None = None
    description: str | None = None
    acceptance_criteria: list[Any] = Field(default_factory=list)
    task_status: str = "TO_DO"
    priority: str = "NORMAL"
    due_date: datetime.date | None = None
    assignee_id: uuid.UUID | None = None


class UpdateRequirementRequest(BaseModel):
    """All fields optional; the router calls `.model_dump(exclude_unset=True)`
    so a field the client omits is left untouched, while a field sent as
    explicit `null` (e.g. `assignee_id`, `phase_id`, `sprint_id`) is actually
    cleared — plain `None`-means-unchanged can't express that distinction."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: str | None = None
    phase_id: uuid.UUID | None = None
    sprint_id: uuid.UUID | None = None
    acceptance_criteria: list[Any] | None = None
    task_status: str | None = None
    priority: str | None = None
    due_date: datetime.date | None = None
    assignee_id: uuid.UUID | None = None


class RequirementResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    phase_id: uuid.UUID | None
    sprint_id: uuid.UUID | None
    key: str
    title: str
    description: str | None
    status: str
    acceptance_criteria: list[Any]
    task_status: str
    priority: str
    due_date: datetime.date | None
    assignee_id: uuid.UUID | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class RequirementEvidenceLinkResponse(BaseModel):
    evidence_chunk_id: uuid.UUID
    relation_type: str
    confidence: float | None
    rationale: str | None


class DeliveryRecordResponse(BaseModel):
    id: uuid.UUID
    requirement_id: uuid.UUID
    status: str
    source_record_id: uuid.UUID | None
    evidence_summary: str | None
    verified_by: uuid.UUID | None
    verified_at: datetime.datetime | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class RequirementDetailResponse(BaseModel):
    requirement: RequirementResponse
    evidence_links: list[RequirementEvidenceLinkResponse]
    delivery_records: list[DeliveryRecordResponse]


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1)


class UpdateCommentRequest(BaseModel):
    body: str = Field(min_length=1)


class RequirementCommentResponse(BaseModel):
    id: uuid.UUID
    requirement_id: uuid.UUID
    author_id: uuid.UUID
    author_display_name: str
    author_email: str
    body: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class RequirementHistoryEntryResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    field: str | None
    old_value: Any | None
    new_value: Any | None
    actor_id: uuid.UUID | None
    actor_display_name: str | None
    actor_email: str | None
    created_at: datetime.datetime
    metadata: dict[str, Any]
