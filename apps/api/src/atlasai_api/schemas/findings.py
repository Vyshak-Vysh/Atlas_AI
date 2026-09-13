from __future__ import annotations

import datetime
import uuid
from typing import Any

from pydantic import BaseModel


class FindingCitationResponse(BaseModel):
    evidence_chunk_id: uuid.UUID
    citation_label: str | None
    quote: str
    location: dict[str, Any]


class FindingResponse(BaseModel):
    id: uuid.UUID
    agent_run_id: uuid.UUID
    project_id: uuid.UUID
    status: str
    summary: str
    facts: list[Any]
    inferences: list[Any]
    conflicts: list[Any]
    missing_evidence: list[Any]
    confidence: float | None
    requires_human_review: bool
    citations: list[FindingCitationResponse]
    created_at: datetime.datetime
