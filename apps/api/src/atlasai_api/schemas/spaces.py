from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, Field

from atlasai_api.schemas.actions import ActionResponse
from atlasai_api.schemas.findings import FindingResponse
from atlasai_api.schemas.projects import ProjectResponse


class CreateSpaceRequest(BaseModel):
    tenant_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)


class SpaceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    color: str | None
    status: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class SpaceOverviewResponse(BaseModel):
    space: SpaceResponse
    project_count: int


class UpdateSpaceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    color: str | None = Field(default=None, max_length=20)
    status: str | None = None


# --- Space-level rollups --------------------------------------------------
# A Space groups several Projects for one client/initiative; these endpoints
# answer "how is this client doing overall" by aggregating already-verified,
# per-project data across every project in the space — never a new LLM
# computation, same "aggregation of verified rows" principle as
# ProjectReportResponse (see schemas/reports.py's docstring).


class SpaceFindingItem(BaseModel):
    project: ProjectResponse
    finding: FindingResponse


class SpaceActionItem(BaseModel):
    project: ProjectResponse
    action: ActionResponse


class SpaceProjectSummary(BaseModel):
    """One row of the space-level report's per-project breakdown table."""

    project: ProjectResponse
    total_requirements: int
    requirements_delivered: int
    total_findings: int
    pending_approvals: int


class SpaceFindingStatusCount(BaseModel):
    status: str
    count: int


class SpaceReportResponse(BaseModel):
    space: SpaceResponse
    generated_at: datetime.datetime
    project_count: int
    total_requirements: int
    requirements_delivered: int
    total_findings: int
    findings_by_status: list[SpaceFindingStatusCount]
    total_pending_approvals: int
    projects: list[SpaceProjectSummary]
    recent_findings: list[SpaceFindingItem]
