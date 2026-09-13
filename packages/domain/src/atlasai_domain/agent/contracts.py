"""Per-state I/O contracts for the agent state machine (TD_v2.md §5 "State
contracts"). Models that are also useful outside the agent (evidence,
findings) live in atlasai_domain.contracts and are re-exported here for
convenience.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from atlasai_domain.contracts.evidence import EvidenceCandidate
from atlasai_domain.contracts.findings import FindingOutput
from atlasai_domain.enums import ActionType, AgentRunIntent

__all__ = [
    "ActionDecisionOutput",
    "ClassifyOutput",
    "EvidenceCandidate",
    "FindingOutput",
    "PlanOutput",
    "RerankOutput",
    "RetrieveOutput",
    "VerifyOutput",
]


class ClassifyOutput(BaseModel):
    """CLASSIFY: determine intent and risk (TD_v2.md §5)."""

    intent: AgentRunIntent
    risk_level: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    rationale: str = Field(min_length=1)


class PlanOutput(BaseModel):
    """PLAN: create subqueries and allowlisted tools (TD_v2.md §5)."""

    subqueries: list[str] = Field(min_length=1)
    allowed_tools: list[str] = Field(min_length=1)
    requires_action: bool = False


class RetrieveOutput(BaseModel):
    """RETRIEVE: permission-filtered hybrid search results, one entry per
    subquery from PlanOutput."""

    subquery: str
    candidates: list[EvidenceCandidate]


class RerankOutput(BaseModel):
    """RERANK: dedupe, score, and diversify evidence across all subqueries."""

    ranked: list[EvidenceCandidate]
    dropped_duplicate_count: int = 0


class VerifyOutput(BaseModel):
    """VERIFY: validate citations, permissions, output schema, and
    unsupported claims before a finding is persisted."""

    citations_valid: bool
    permission_valid: bool
    schema_valid: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    notes: str | None = None

    @property
    def passed(self) -> bool:
        return self.citations_valid and self.permission_valid and self.schema_valid and not self.unsupported_claims


class ActionDecisionOutput(BaseModel):
    """ACTION_DECISION: determine whether a write is requested."""

    requires_action: bool
    action_type: ActionType | None = None
    reason: str = Field(min_length=1)
    action_payload: dict[str, object] | None = None
    """Draft payload to be frozen at PROPOSE_ACTION if requires_action is true."""

    project_id: UUID | None = None
