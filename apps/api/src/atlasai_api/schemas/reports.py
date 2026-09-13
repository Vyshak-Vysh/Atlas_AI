from __future__ import annotations

import datetime

from pydantic import BaseModel

from atlasai_api.schemas.findings import FindingResponse
from atlasai_api.schemas.projects import PhaseResponse, ProjectResponse


class PhaseProgress(BaseModel):
    phase: PhaseResponse
    requirement_count: int
    requirements_delivered: int


class FindingStatusCount(BaseModel):
    status: str
    count: int


class ProjectReportResponse(BaseModel):
    """A deterministic aggregation of already-verified project data — never
    LLM-generated — so the report itself carries no fabrication risk. Every
    figure here is a direct count/read from the same tables the rest of the
    product treats as the system of record (ATLASAI_MASTER_SPEC.md §2: "LLM
    output is never the system of record")."""

    project: ProjectResponse
    generated_at: datetime.datetime
    phase_progress: list[PhaseProgress]
    total_requirements: int
    total_sources: int
    latest_source_at: datetime.datetime | None
    total_findings: int
    findings_by_status: list[FindingStatusCount]
    recent_findings: list[FindingResponse]
    pending_approvals: int
    member_count: int
