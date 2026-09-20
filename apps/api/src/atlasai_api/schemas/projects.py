from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, EmailStr, Field


class CreateProjectRequest(BaseModel):
    tenant_id: uuid.UUID
    name: str = Field(min_length=1, max_length=250)
    client_name: str | None = Field(default=None, max_length=250)
    code: str | None = Field(default=None, max_length=80)
    timezone: str = "UTC"
    space_id: uuid.UUID | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    space_id: uuid.UUID | None
    name: str
    client_name: str | None
    code: str | None
    status: str
    timezone: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class CreatePhaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phase_number: int
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None


class PhaseResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    phase_number: int
    start_date: datetime.date | None
    end_date: datetime.date | None
    status: str

    model_config = {"from_attributes": True}


class AddProjectMemberRequest(BaseModel):
    email: EmailStr
    role: str


class ProjectMemberResponse(BaseModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: str


class ProjectMemberDetailResponse(BaseModel):
    project_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: str
    joined_at: datetime.datetime


class ProjectOverviewResponse(BaseModel):
    project: ProjectResponse
    phases: list[PhaseResponse]
    member_count: int


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=250)
    client_name: str | None = Field(default=None, max_length=250)
    status: str | None = None
    space_id: uuid.UUID | None = None
