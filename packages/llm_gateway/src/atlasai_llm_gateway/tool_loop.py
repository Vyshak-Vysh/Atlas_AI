"""Bounded tool-use loop against the Anthropic Messages API.

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
    pure protocol adapter.

2.  **Every tool result for one assistant turn goes back in a single user
    message.** Splitting `tool_result` blocks across several messages
    teaches the model to stop issuing parallel calls, so results are
    batched exactly as the provider expects - including failures, which
    come back as `is_error` blocks rather than being silently dropped, so
    the model can recover by trying a different query instead of stalling.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import anthropic
from anthropic import AsyncAnthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from atlasai_domain.agent.tools import ToolCall, ToolResult, ToolSpec
from atlasai_llm_gateway.cost_tracking import TokenUsage
from atlasai_llm_gateway.settings import AnthropicSettings

_RETRYABLE_EXCEPTIONS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
)

ToolExecutor = Callable[[ToolCall], Awaitable[ToolResult]]


class ToolLoopRefusalError(Exception):
    """The model declined the request (`stop_reason == "refusal"`). Raised
    rather than returning a partial transcript, so a refusal can never be
    mistaken for "the evidence did not support an answer"."""

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
    """Runs `run()` against Anthropic's Messages API with a tool allowlist.

    `settings` and `client` are injectable so the loop's protocol behaviour
    (result batching, iteration bounds, refusal handling) can be tested
    against a scripted provider without an API key — the default path still
    reads environment-driven settings and builds its own client.
    """

    def __init__(
        self, *, settings: AnthropicSettings | None = None, client: AsyncAnthropic | None = None
    ) -> None:
        self._settings = settings or AnthropicSettings()
        self._client = client or AsyncAnthropic(api_key=self._settings.anthropic_api_key)

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
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
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        self._settings.require_api_key()
        return await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
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
        tool_params = [t.to_provider_dict() for t in tools]
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]

        result = ToolLoopResult(final_text="", iterations=0, stop_reason=None, model=resolved_model)

        for _ in range(max_iterations):
            response = await self._create(
                model=resolved_model,
                max_tokens=max_tokens or self._settings.llm_max_tokens_default,
                system=system,
                messages=messages,
                tools=tool_params,
            )
            result.iterations += 1
            result.input_tokens += response.usage.input_tokens
            result.output_tokens += response.usage.output_tokens
            result.stop_reason = response.stop_reason
            result.model = response.model

            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                raise ToolLoopRefusalError(
                    category=getattr(details, "category", None) if details else None,
                    explanation=getattr(details, "explanation", None) if details else None,
                )

            tool_use_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
            text_blocks = [b for b in response.content if getattr(b, "type", None) == "text"]
            if text_blocks:
                result.final_text = "\n".join(b.text for b in text_blocks)

            if response.stop_reason != "tool_use" or not tool_use_blocks:
                break

            # Echo the assistant turn back verbatim. The provider requires
            # each tool_result to answer a tool_use block it can still see.
            messages.append({"role": "assistant", "content": response.content})

            tool_result_blocks: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                # `block.input` is already a parsed object from the SDK; it is
                # never string-matched - escaping differs across models.
                raw_input = block.input if isinstance(block.input, dict) else {}
                call = ToolCall(call_id=block.id, name=block.name, arguments=raw_input)
                tool_result = await execute(call)

                result.tool_calls.append(call)
                result.tool_results.append(tool_result)
                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_result.call_id,
                        "content": tool_result.content,
                        "is_error": tool_result.is_error,
                    }
                )

            # All results for this turn in one user message - see module docstring.
            messages.append({"role": "user", "content": tool_result_blocks})

        return result

    async def aclose(self) -> None:
        await self._client.close()
