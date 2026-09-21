"""Unit tests for the bounded tool-use loop (packages/llm_gateway/tool_loop.py).

The loop is exercised against a scripted fake provider rather than the live
API, so these assertions run in CI without an API key and pin down the
protocol details that are easy to regress and expensive to notice:

*   all `function_response` parts for one model turn go back in a **single**
    user message (splitting them trains the model out of parallel calls),
*   the model turn is echoed back before its results,
*   `max_iterations` is a hard stop, not a suggestion,
*   a refusal raises rather than returning an empty-looking success.

Responses are built from the real `google.genai.types` models, so the
fakes cannot drift from the shape the SDK actually returns.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from google import genai
from google.genai import types

from atlasai_domain.agent.tools import ToolCall, ToolResult, ToolSpec
from atlasai_llm_gateway.settings import GeminiSettings, MissingAPIKeyError
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


def _response(
    parts: list[types.Part],
    *,
    finish_reason: types.FinishReason = types.FinishReason.STOP,
    model: str = "gemini-3.8-flash",
) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        model_version=model,
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts), finish_reason=finish_reason)],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=10, candidates_token_count=5),
    )


def _text(text: str) -> types.Part:
    return types.Part(text=text)


def _function_call(name: str, payload: dict[str, Any], *, call_id: str | None = None) -> types.Part:
    return types.Part(function_call=types.FunctionCall(id=call_id, name=name, args=payload))


class _ScriptedGateway(ToolLoopGateway):
    """A ToolLoopGateway whose provider call replays a fixed script and
    records the exact `contents` list it was handed each turn."""

    def __init__(self, script: list[types.GenerateContentResponse]) -> None:
        # Settings are injected with a dummy key and no real client is built,
        # so the loop's own logic is exercised without any network or API key.
        super().__init__(
            settings=GeminiSettings(gemini_api_key="test-key-not-used"),
            client=cast(genai.Client, object()),
        )
        self._script = script
        self._turn = 0
        self.sent_contents: list[list[types.Content]] = []

    async def _create(self, **kwargs: Any) -> Any:  # type: ignore[override]
        # Snapshot of the contents as they looked at call time.
        self.sent_contents.append(list(kwargs["contents"]))
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
            _response([_function_call("search_evidence", {"query": "sso"})]),
            _response([_text("I searched for SSO and found the SOW clause.")]),
        ]
    )

    result = await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=6)

    assert result.iterations == 2
    assert result.stop_reason == "end_turn"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_evidence"
    assert result.tool_calls[0].arguments == {"query": "sso"}
    assert "SOW clause" in result.final_text
    assert result.model == "gemini-3.8-flash"


async def test_all_tool_results_for_one_turn_go_back_in_a_single_message() -> None:
    """Three parallel function calls must produce exactly one user message
    carrying three function_response parts."""
    gateway = _ScriptedGateway(
        [
            _response(
                [
                    _function_call("search_evidence", {"query": "sso"}),
                    _function_call("search_evidence", {"query": "mfa"}),
                    _function_call("search_evidence", {"query": "notifications"}),
                ]
            ),
            _response([_text("done")]),
        ]
    )

    result = await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=6)

    assert len(result.tool_calls) == 3
    second_turn = gateway.sent_contents[1]
    # [user prompt, model turn, one user message of results]
    assert len(second_turn) == 3
    assert second_turn[1].role == "model"
    results_message = second_turn[2]
    assert results_message.role == "user"
    assert results_message.parts is not None and len(results_message.parts) == 3
    responses = [p.function_response for p in results_message.parts]
    assert all(r is not None and r.name == "search_evidence" for r in responses)
    assert [r.response for r in responses if r is not None] == [
        {"output": "result for sso"},
        {"output": "result for mfa"},
        {"output": "result for notifications"},
    ]


async def test_call_ids_are_synthesized_when_the_provider_omits_them() -> None:
    """The Gemini Developer API pairs responses by name and position and
    usually sends no `id`; the domain-side transcript still needs a unique
    handle per call, and a provider-supplied id must be passed back as-is."""
    gateway = _ScriptedGateway(
        [
            _response(
                [
                    _function_call("search_evidence", {"query": "a"}),
                    _function_call("search_evidence", {"query": "b"}, call_id="fc_provided"),
                ]
            ),
            _response([_text("done")]),
        ]
    )

    result = await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=6)

    ids = [c.call_id for c in result.tool_calls]
    assert len(set(ids)) == 2
    assert ids[1] == "fc_provided"
    sent_back = gateway.sent_contents[1][2].parts
    assert sent_back is not None
    assert sent_back[0].function_response is not None and sent_back[0].function_response.id is None
    assert sent_back[1].function_response is not None and sent_back[1].function_response.id == "fc_provided"


async def test_max_iterations_is_a_hard_stop() -> None:
    """A model that never stops asking for tools must not extend the run."""
    always_tools = _response([_function_call("search_evidence", {"query": "again"})])
    gateway = _ScriptedGateway([always_tools])

    result = await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=4)

    assert result.iterations == 4
    assert result.stop_reason == "tool_use"
    assert len(result.tool_calls) == 4


async def test_failed_tool_result_is_returned_to_the_model_not_dropped() -> None:
    async def _failing_executor(call: ToolCall) -> ToolResult:
        return ToolResult(call_id=call.call_id, name=call.name, content="budget exhausted", is_error=True)

    gateway = _ScriptedGateway(
        [
            _response([_function_call("search_evidence", {"query": "sso"})]),
            _response([_text("ok, answering with what I have")]),
        ]
    )

    result = await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_failing_executor, max_iterations=4)

    results_message = gateway.sent_contents[1][2]
    assert results_message.parts is not None
    function_response = results_message.parts[0].function_response
    assert function_response is not None
    # The provider's documented convention: failures go under "error".
    assert function_response.response == {"error": "budget exhausted"}
    assert result.tool_results[0].is_error


async def test_blocked_response_raises_rather_than_returning_a_quiet_empty_result() -> None:
    refusal = _response([], finish_reason=types.FinishReason.SAFETY)
    gateway = _ScriptedGateway([refusal])

    with pytest.raises(ToolLoopRefusalError) as excinfo:
        await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=3)
    assert excinfo.value.category == "SAFETY"


async def test_blocked_prompt_raises_even_though_there_are_no_candidates() -> None:
    """A prompt the provider refuses to run at all comes back with
    `prompt_feedback` and an empty candidate list - not a finish reason."""
    blocked = types.GenerateContentResponse(
        prompt_feedback=types.GenerateContentResponsePromptFeedback(
            block_reason=types.BlockedReason.PROHIBITED_CONTENT, block_reason_message="nope"
        )
    )
    gateway = _ScriptedGateway([blocked])

    with pytest.raises(ToolLoopRefusalError) as excinfo:
        await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=3)
    assert excinfo.value.category == "PROHIBITED_CONTENT"
    assert excinfo.value.explanation == "nope"


async def test_truncated_final_turn_is_reported_not_hidden() -> None:
    gateway = _ScriptedGateway([_response([_text("half an ans")], finish_reason=types.FinishReason.MAX_TOKENS)])

    result = await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=3)

    assert result.stop_reason == "max_tokens"
    assert result.final_text == "half an ans"


async def test_token_usage_accumulates_across_turns_and_counts_thinking_as_output() -> None:
    thinking = types.GenerateContentResponse(
        model_version="gemini-3.8-flash",
        candidates=[types.Candidate(content=types.Content(role="model", parts=[_text("done")]), finish_reason="STOP")],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=10, candidates_token_count=5, thoughts_token_count=7
        ),
    )
    gateway = _ScriptedGateway([_response([_function_call("search_evidence", {"query": "a"})]), thinking])

    result = await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=4)

    # Turn 1: 10 in / 5 out. Turn 2: 10 in / 5 + 7 thinking out.
    assert result.input_tokens == 20
    assert result.output_tokens == 17
    assert result.total_tokens == 37


def test_tool_spec_serializes_to_the_provider_shape() -> None:
    payload = _SPEC.to_provider_dict()
    assert set(payload) == {"name", "description", "parameters_json_schema"}
    assert payload["parameters_json_schema"]["additionalProperties"] is False
    # And the provider accepts it verbatim.
    declaration = types.FunctionDeclaration(**payload)
    assert declaration.parameters_json_schema == _SPEC.input_schema


async def test_missing_api_key_raises_an_actionable_error() -> None:
    """With no key configured the provider SDK refuses to even construct a
    client ("No API key was provided"), which shows up on an agent run as
    an opaque FAILED and reads like a pipeline bug. The gateway must name
    the variable to set instead - and must not try to build the client
    before checking."""
    gateway = ToolLoopGateway(settings=GeminiSettings(gemini_api_key=""))
    with pytest.raises(MissingAPIKeyError) as excinfo:
        await gateway.run(system="s", user_content="u", tools=[_SPEC], execute=_echo_executor, max_iterations=2)

    message = str(excinfo.value)
    assert "GEMINI_API_KEY" in message
    assert ".env" in message
