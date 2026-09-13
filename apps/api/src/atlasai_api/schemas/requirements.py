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
    description: str | None = None
    acceptance_criteria: list[Any] = Field(default_factory=list)


class RequirementResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    phase_id: uuid.UUID | None
    key: str
    title: str
    description: str | None
    status: str
    acceptance_criteria: list[Any]
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
