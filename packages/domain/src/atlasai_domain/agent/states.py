"""Agent state enum and transition table (ATLASAI_MASTER_SPEC.md §4).

Main flow:
    RECEIVED -> CLASSIFY -> PLAN -> INVESTIGATE -> RERANK -> ANALYZE
    -> VERIFY -> FINDING -> ACTION_DECISION -> COMPLETE

INVESTIGATE is the bounded tool-calling loop (agent/tools.py): the model
chooses which allowlisted read tools to call and with what arguments, and
the loop runs until it stops requesting tools or a budget is spent.
RETRIEVE is the deterministic single-shot alternative to it (one hybrid
search per planned subquery, no model in the loop) and remains legal from
PLAN so a run can be forced down the cheaper path via
`agent_runs.model_policy`; both converge on RERANK.

Action branch:
    ACTION_DECISION -> PROPOSE_ACTION -> WAIT_APPROVAL -> EXECUTE -> COMPLETE

Failure branch (kept out of TRANSITION_TABLE as a blanket rule rather than
duplicated on every row): any state -> RETRY (within budget) -> the same
state again, or any state -> FAILED (terminal, audited).
"""

from __future__ import annotations

from enum import StrEnum


class AgentState(StrEnum):
    RECEIVED = "RECEIVED"
    CLASSIFY = "CLASSIFY"
    PLAN = "PLAN"
    INVESTIGATE = "INVESTIGATE"
    RETRIEVE = "RETRIEVE"
    RERANK = "RERANK"
    ANALYZE = "ANALYZE"
    VERIFY = "VERIFY"
    FINDING = "FINDING"
    ACTION_DECISION = "ACTION_DECISION"
    PROPOSE_ACTION = "PROPOSE_ACTION"
    WAIT_APPROVAL = "WAIT_APPROVAL"
    EXECUTE = "EXECUTE"
    COMPLETE = "COMPLETE"
    RETRY = "RETRY"
    FAILED = "FAILED"


TERMINAL_STATES: frozenset[AgentState] = frozenset({AgentState.COMPLETE, AgentState.FAILED})

# Explicit forward adjacency. RETRY/FAILED are reachable from every
# non-terminal state and are intentionally not repeated on every row below;
# `can_transition` checks that rule separately.
TRANSITION_TABLE: dict[AgentState, frozenset[AgentState]] = {
    AgentState.RECEIVED: frozenset({AgentState.CLASSIFY}),
    AgentState.CLASSIFY: frozenset({AgentState.PLAN}),
    AgentState.PLAN: frozenset({AgentState.INVESTIGATE, AgentState.RETRIEVE}),
    AgentState.INVESTIGATE: frozenset({AgentState.RERANK}),
    AgentState.RETRIEVE: frozenset({AgentState.RERANK}),
    AgentState.RERANK: frozenset({AgentState.ANALYZE}),
    AgentState.ANALYZE: frozenset({AgentState.VERIFY}),
    AgentState.VERIFY: frozenset({AgentState.FINDING}),
    AgentState.FINDING: frozenset({AgentState.ACTION_DECISION}),
    AgentState.ACTION_DECISION: frozenset({AgentState.PROPOSE_ACTION, AgentState.COMPLETE}),
    AgentState.PROPOSE_ACTION: frozenset({AgentState.WAIT_APPROVAL}),
    AgentState.WAIT_APPROVAL: frozenset({AgentState.EXECUTE, AgentState.FAILED}),
    AgentState.EXECUTE: frozenset({AgentState.COMPLETE}),
    # RETRY re-enters whichever state raised it; the runner tracks that
    # target separately (see apps/ai_atlas/agent_runner/runner.py), so RETRY
    # has no fixed forward edge here.
    AgentState.RETRY: frozenset(AgentState) - TERMINAL_STATES - {AgentState.RETRY},
    AgentState.COMPLETE: frozenset(),
    AgentState.FAILED: frozenset(),
}


def can_transition(current: AgentState, next_: AgentState) -> bool:
    """Whether `next_` is a legal transition from `current`.

    RETRY and FAILED are legal from any non-terminal state (the spec's
    "any state -> RETRY within budget" / "any state -> FAILED" rule) and are
    therefore checked here rather than listed in every TRANSITION_TABLE row.
    """
    if current in TERMINAL_STATES:
        return False
    if next_ in (AgentState.RETRY, AgentState.FAILED):
        return True
    return next_ in TRANSITION_TABLE.get(current, frozenset())


def is_terminal(state: AgentState) -> bool:
    return state in TERMINAL_STATES
