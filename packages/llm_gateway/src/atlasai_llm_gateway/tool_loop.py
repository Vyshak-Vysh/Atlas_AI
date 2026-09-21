"""Bounded tool-use loop against the Gemini `generate_content` API.

This is the real agentic surface: the model is given a closed set of
`ToolSpec`s and decides, per turn, which of them to call and with what
arguments. The loop runs until the model stops requesting tools, the
iteration budget is spent, or the model refuses.

Two deliberate design choices:

1.  **The executor is injected.** This package must not import the database
    or the agent runner (it sits below both in the dependency graph), so
    the caller passes an `execute` coroutine that resolves a `ToolCall`
    into a `ToolResult`. Budget enforcement and project scoping therefore
    live with the caller that owns the DB session, and this module stays a
    pure protocol adapter. The SDK's automatic function calling is switched
    off for the same reason - nothing may dispatch a tool but the caller.

2.  **Every tool result for one model turn goes back in a single user
    message.** Splitting `function_response` parts across several messages
    teaches the model to stop issuing parallel calls, so results are
    batched exactly as the provider expects - including failures, which
    come back under the provider's `error` key rather than being silently
    dropped, so the model can recover by trying a different query instead
    of stalling.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from atlasai_domain.agent.tools import ToolCall, ToolResult, ToolSpec
from atlasai_llm_gateway import _gemini
from atlasai_llm_gateway.cost_tracking import TokenUsage
from atlasai_llm_gateway.settings import GeminiSettings

ToolExecutor = Callable[[ToolCall], Awaitable[ToolResult]]


class ToolLoopRefusalError(Exception):
    """The model declined the request (a blocked prompt, or a candidate
    that stopped for a safety reason). Raised rather than returning a
    partial transcript, so a refusal can never be mistaken for "the
    evidence did not support an answer"."""

    def __init__(self, category: str | None, explanation: str | None) -> None:
        self.category = category
        self.explanation = explanation
        super().__init__(f"model refused during tool loop (category={category}): {explanation}")


@dataclass
class ToolLoopResult:
    """Outcome of a completed loop.

    `final_text` is the model's closing prose. The agent does not treat it
    as the answer - ANALYZE re-derives a structured, citation-validated
    finding from the evidence the loop gathered. It is retained for the
    step transcript so a human reviewing the run can see the model's own
    reasoning about which tools it chose.

    `stop_reason` is provider-neutral, because the agent records it on the
    step and that record should not change shape with the model vendor:
    `"end_turn"` - the model finished without asking for more tools;
    `"tool_use"` - the model still wanted tools when the iteration budget
    ran out; anything else is the provider's own finish reason, lower-cased
    (e.g. `"max_tokens"`).
    """

    final_text: str
    iterations: int
    stop_reason: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def usage(self) -> TokenUsage:
        return TokenUsage(model=self.model, input_tokens=self.input_tokens, output_tokens=self.output_tokens)


class ToolLoopGateway:
    """Runs `run()` against Gemini's `generate_content` API with a tool
    allowlist.

    `settings` and `client` are injectable so the loop's protocol behaviour
    (result batching, iteration bounds, refusal handling) can be tested
    against a scripted provider without an API key — the default path still
    reads environment-driven settings and builds its own client on first
    use.
    """

    def __init__(self, *, settings: GeminiSettings | None = None, client: genai.Client | None = None) -> None:
        self._settings = settings or GeminiSettings()
        self._client = client

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = _gemini.build_client(self._settings)
        return self._client

    @retry(
        retry=retry_if_exception(_gemini.is_retryable),
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        contents: list[types.ContentUnion],
        tools: list[types.Tool],
    ) -> types.GenerateContentResponse:
        self._settings.require_api_key()
        return await self._get_client().aio.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )

    async def run(
        self,
        *,
        system: str,
        user_content: str,
        tools: list[ToolSpec],
        execute: ToolExecutor,
        max_iterations: int,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> ToolLoopResult:
        """Drive the loop to completion or to its iteration budget.

        `max_iterations` is a hard stop, not a hint: when it is reached the
        loop returns what it has rather than issuing another request, so a
        model that keeps asking for tools cannot extend the run. The caller
        additionally enforces a per-tool call budget inside `execute`.
        """
        resolved_model = model or self._settings.llm_model_default
        tool_params = [
            types.Tool(function_declarations=[types.FunctionDeclaration(**t.to_provider_dict()) for t in tools])
        ]
        contents: list[types.ContentUnion] = [types.Content(role="user", parts=[types.Part(text=user_content)])]

        result = ToolLoopResult(final_text="", iterations=0, stop_reason=None, model=resolved_model)

        for _ in range(max_iterations):
            response = await self._create(
                model=resolved_model,
                max_tokens=max_tokens or self._settings.llm_max_tokens_default,
                system=system,
                contents=contents,
                tools=tool_params,
            )
            result.iterations += 1
            turn_usage = _gemini.usage(response, requested_model=resolved_model)
            result.input_tokens += turn_usage.input_tokens
            result.output_tokens += turn_usage.output_tokens
            result.model = turn_usage.model

            refused = _gemini.refusal(response)
            if refused is not None:
                category, explanation = refused
                raise ToolLoopRefusalError(category=category, explanation=explanation)

            candidate = _gemini.first_candidate(response)
            model_turn = candidate.content if candidate is not None else None
            parts = list(model_turn.parts or []) if model_turn is not None else []
            function_calls = [p.function_call for p in parts if p.function_call is not None]
            # Thought parts are the model's reasoning, not its answer; they are
            # only present when explicitly requested, but never belong in prose.
            text_parts = [p.text for p in parts if p.text and not p.thought]
            if text_parts:
                result.final_text = "\n".join(text_parts)

            if not function_calls or model_turn is None:
                finish = _gemini.finish_reason_name(response)
                result.stop_reason = "end_turn" if finish == "STOP" else (finish.lower() if finish else None)
                break
            result.stop_reason = "tool_use"

            # Echo the model turn back verbatim. The provider matches each
            # function_response to a function_call it can still see.
            contents.append(model_turn)

            response_parts: list[types.Part] = []
            for index, function_call in enumerate(function_calls):
                # The Gemini Developer API usually leaves `id` unset and pairs
                # responses by name and position; a stable synthetic id keeps
                # the domain-side transcript addressable either way.
                call_id = function_call.id or f"call_{result.iterations}_{index}"
                # `args` is already a parsed object from the SDK; it is never
                # string-matched - escaping differs across models.
                arguments: dict[str, Any] = dict(function_call.args) if function_call.args else {}
                call = ToolCall(call_id=call_id, name=function_call.name or "", arguments=arguments)
                tool_result = await execute(call)

                result.tool_calls.append(call)
                result.tool_results.append(tool_result)
                payload = {"error": tool_result.content} if tool_result.is_error else {"output": tool_result.content}
                response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=function_call.id, name=function_call.name, response=payload
                        )
                    )
                )

            # All results for this turn in one user message - see module docstring.
            contents.append(types.Content(role="user", parts=response_parts))

        return result

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aio.aclose()
