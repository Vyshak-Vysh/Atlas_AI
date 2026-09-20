"""Unit tests for the bounded tool-use loop (packages/llm_gateway/tool_loop.py).

The loop is exercised against a scripted fake provider rather than the live
API, so these assertions run in CI without an API key and pin down the
protocol details that are easy to regress and expensive to notice:

*   all `tool_result` blocks for one assistant turn go back in a **single**
    user message (splitting them trains the model out of parallel calls),
*   the assistant turn is echoed back before its results,
*   `max_iterations` is a hard stop, not a suggestion,
*   a refusal raises rather than returning an empty-looking success.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from anthropic import AsyncAnthropic

from atlasai_domain.agent.tools import ToolCall, ToolResult, ToolSpec
from atlasai_llm_gateway.settings import AnthropicSettings
from atlasai_llm_gateway.tool_loop import ToolLoopGateway, ToolLoopRefusalError

_SPEC = ToolSpec(
    name="search_evidence",
    description="Search project evidence.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    },
)


class _Block:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class _Usage:
    def __init__(self, input_tokens: int = 10, output_tokens: int = 5) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Response:
    def __init__(self, *, stop_reason: str, content: list[Any], model: str = "claude-sonnet-5") -> None:
        self.stop_reason = stop_reason
        self.content = content
        self.model = model
        self.usage = _Usage()
        self.stop_details = None


def _text(text: str) -> _Block:
    return _Block(type="text", text=text)


def _tool_use(call_id: str, name: str, payload: dict[str, Any]) -> _Block:
    return _Block(type="tool_use", id=call_id, name=name, input=payload)


class _ScriptedGateway(ToolLoopGateway):
    """A ToolLoopGateway whose provider call replays a fixed script and
    records the exact `messages` array it was handed each turn."""

    def __init__(self, script: list[_Response]) -> None:
        # Settings are injected with a dummy key and no client is built, so
        # the loop's own logic is exercised without any network or API key.
        super().__init__(
            settings=AnthropicSettings(anthropic_api_key="test-key-not-used"),
            client=cast(AsyncAnthropic, object()),
        )
        self._script = script
        self._turn = 0
        self.sent_messages: list[list[dict[str, Any]]] = []

    async def _create(self, **kwargs: Any) -> Any:  # type: ignore[override]
        # Deep-ish copy of the messages as they looked at call time.
        self.sent_messages.append([dict(m) for m in kwargs["messages"]])
        response = self._script[min(self._turn, len(self._script) - 1)]
        self._turn += 1
        return response

    async def aclose(self) -> None:
        return None


async def _echo_executor(call: ToolCall) -> ToolResult:
    return ToolResult(call_id=call.call_id, name=call.name, content=f"result for {call.arguments.get('query')}")


async def test_loop_stops_when_model_stops_requesting_tools() -> None:
    gateway = _ScriptedGateway(
        [
            _Response(stop_reason="tool_use", content=[_tool_use("t1", "search_evidence", {"query": "sso"})]),
            _Response(stop_reason="end_turn", content=[_text("I searched for SSO and found the SOW clause.")]),
        ]
    )

    result = await gateway.run(
        system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=6
    )

    assert result.iterations == 2
    assert result.stop_reason == "end_turn"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_evidence"
    assert "SOW clause" in result.final_text


async def test_all_tool_results_for_one_turn_go_back_in_a_single_message() -> None:
    """Three parallel tool_use blocks must produce exactly one user message
    carrying three tool_result blocks."""
    gateway = _ScriptedGateway(
        [
            _Response(
                stop_reason="tool_use",
                content=[
                    _tool_use("t1", "search_evidence", {"query": "sso"}),
                    _tool_use("t2", "search_evidence", {"query": "mfa"}),
                    _tool_use("t3", "search_evidence", {"query": "notifications"}),
                ],
            ),
            _Response(stop_reason="end_turn", content=[_text("done")]),
        ]
    )

    result = await gateway.run(
        system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=6
    )

    assert len(result.tool_calls) == 3
    second_turn = gateway.sent_messages[1]
    # [user prompt, assistant turn, one user message of results]
    assert len(second_turn) == 3
    assert second_turn[1]["role"] == "assistant"
    results_message = second_turn[2]
    assert results_message["role"] == "user"
    assert len(results_message["content"]) == 3
    assert {b["tool_use_id"] for b in results_message["content"]} == {"t1", "t2", "t3"}
    assert all(b["type"] == "tool_result" for b in results_message["content"])


async def test_max_iterations_is_a_hard_stop() -> None:
    """A model that never stops asking for tools must not extend the run."""
    always_tools = _Response(
        stop_reason="tool_use", content=[_tool_use("t1", "search_evidence", {"query": "again"})]
    )
    gateway = _ScriptedGateway([always_tools])

    result = await gateway.run(
        system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=4
    )

    assert result.iterations == 4
    assert result.stop_reason == "tool_use"
    assert len(result.tool_calls) == 4


async def test_failed_tool_result_is_returned_to_the_model_not_dropped() -> None:
    async def _failing_executor(call: ToolCall) -> ToolResult:
        return ToolResult(call_id=call.call_id, name=call.name, content="budget exhausted", is_error=True)

    gateway = _ScriptedGateway(
        [
            _Response(stop_reason="tool_use", content=[_tool_use("t1", "search_evidence", {"query": "sso"})]),
            _Response(stop_reason="end_turn", content=[_text("ok, answering with what I have")]),
        ]
    )

    result = await gateway.run(
        system="s", user_content="u", tools=[_SPEC], execute=_failing_executor, max_iterations=4
    )

    results_message = gateway.sent_messages[1][2]
    assert results_message["content"][0]["is_error"] is True
    assert result.tool_results[0].is_error


async def test_refusal_raises_rather_than_returning_a_quiet_empty_result() -> None:
    refusal = _Response(stop_reason="refusal", content=[])
    gateway = _ScriptedGateway([refusal])

    with pytest.raises(ToolLoopRefusalError):
        await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=3)


async def test_token_usage_accumulates_across_turns() -> None:
    gateway = _ScriptedGateway(
        [
            _Response(stop_reason="tool_use", content=[_tool_use("t1", "search_evidence", {"query": "a"})]),
            _Response(stop_reason="end_turn", content=[_text("done")]),
        ]
    )

    result = await gateway.run(
        system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=4
    )

    # Two turns at 10 in / 5 out each.
    assert result.input_tokens == 20
    assert result.output_tokens == 10
    assert result.total_tokens == 30


def test_tool_spec_serializes_to_the_provider_shape() -> None:
    payload = _SPEC.to_provider_dict()
    assert set(payload) == {"name", "description", "input_schema"}
    assert payload["input_schema"]["additionalProperties"] is False
