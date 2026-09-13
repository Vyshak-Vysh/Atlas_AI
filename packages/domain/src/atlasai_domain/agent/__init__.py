"""Bounded agent state machine contracts (ATLASAI_MASTER_SPEC.md §4, TD_v2.md §5).

This package only defines the shape of the state machine — states,
transitions, per-state I/O contracts, and run limits. The executor that
actually drives an agent_runs row through these states lives in
apps/ai_atlas/agent_runner (a separate deployable that depends on this
package, packages/db, packages/retrieval, and packages/llm_gateway).
"""

from atlasai_domain.agent.contracts import (
    ActionDecisionOutput,
    ClassifyOutput,
    EvidenceCandidate,
    FindingOutput,
    PlanOutput,
    RerankOutput,
    RetrieveOutput,
    VerifyOutput,
)
from atlasai_domain.agent.events import AgentStepEvent
from atlasai_domain.agent.limits import RunLimits
from atlasai_domain.agent.states import AgentState, can_transition, is_terminal

__all__ = [
    "ActionDecisionOutput",
    "AgentState",
    "AgentStepEvent",
    "ClassifyOutput",
    "EvidenceCandidate",
    "FindingOutput",
    "PlanOutput",
    "RerankOutput",
    "RetrieveOutput",
    "RunLimits",
    "VerifyOutput",
    "can_transition",
    "is_terminal",
]
