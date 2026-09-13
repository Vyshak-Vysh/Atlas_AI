"""Unit tests for the bounded agent state machine's transition rules
(ATLASAI_MASTER_SPEC.md §4)."""

from __future__ import annotations

from atlasai_domain.agent.states import AgentState, can_transition, is_terminal


def test_main_flow_is_linear_and_legal() -> None:
    main_flow = [
        AgentState.RECEIVED,
        AgentState.CLASSIFY,
        AgentState.PLAN,
        AgentState.RETRIEVE,
        AgentState.RERANK,
        AgentState.ANALYZE,
        AgentState.VERIFY,
        AgentState.FINDING,
        AgentState.ACTION_DECISION,
        AgentState.COMPLETE,
    ]
    # strict=False is intentional: main_flow[1:] is always one element
    # shorter than main_flow by construction (we're pairing consecutive
    # states), not a bug to be caught by strict zip.
    for current, next_ in zip(main_flow, main_flow[1:], strict=False):
        assert can_transition(current, next_), f"{current} -> {next_} should be legal"


def test_action_branch_is_legal() -> None:
    action_flow = [
        AgentState.ACTION_DECISION,
        AgentState.PROPOSE_ACTION,
        AgentState.WAIT_APPROVAL,
        AgentState.EXECUTE,
        AgentState.COMPLETE,
    ]
    for current, next_ in zip(action_flow, action_flow[1:], strict=False):
        assert can_transition(current, next_)


def test_retry_and_failed_are_legal_from_any_non_terminal_state() -> None:
    for state in AgentState:
        if is_terminal(state):
            continue
        assert can_transition(state, AgentState.RETRY)
        assert can_transition(state, AgentState.FAILED)


def test_terminal_states_accept_no_further_transitions() -> None:
    for terminal in (AgentState.COMPLETE, AgentState.FAILED):
        for target in AgentState:
            assert not can_transition(terminal, target)


def test_cannot_skip_states_in_main_flow() -> None:
    # RECEIVED must go through CLASSIFY, not straight to RETRIEVE.
    assert not can_transition(AgentState.RECEIVED, AgentState.RETRIEVE)
    # FINDING cannot jump back to RETRIEVE.
    assert not can_transition(AgentState.FINDING, AgentState.RETRIEVE)


def test_wait_approval_can_fail_a_rejected_or_expired_approval() -> None:
    assert can_transition(AgentState.WAIT_APPROVAL, AgentState.FAILED)
    assert can_transition(AgentState.WAIT_APPROVAL, AgentState.EXECUTE)
