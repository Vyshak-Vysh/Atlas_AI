"""Anthropic provider adapter.

Structured outputs use `client.messages.parse(..., output_format=SomeModel)`
-> `response.parsed_output` — the current, non-deprecated API (verified
against the bundled claude-api skill, not assumed from training data).
`response.stop_reason == "refusal"` is always checked before reading
content; retries cover 429/5xx/network per Anthropic's documented typed
exception hierarchy.
"""

from __future__ import annotations

from typing import TypeVar

import anthropic
from anthropic import AsyncAnthropic
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from atlasai_llm_gateway.cost_tracking import TokenUsage
from atlasai_llm_gateway.settings import AnthropicSettings

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_EXCEPTIONS = (
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    anthropic.APIConnectionError,
)


class LLMRefusalError(Exception):
    def __init__(self, category: str | None, explanation: str | None) -> None:
        self.category = category
        self.explanation = explanation
        super().__init__(f"model refused to respond (category={category}): {explanation}")


class StructuredOutputError(Exception):
    pass


class StructuredCompletion:
    def __init__(self, parsed: BaseModel, usage: TokenUsage, model: str, prompt_version: str) -> None:
        self.parsed = parsed
        self.usage = usage
        self.model = model
        self.prompt_version = prompt_version


class AnthropicGateway:
    def __init__(self) -> None:
        self._settings = AnthropicSettings()
        self._client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)

    @property
    def prompt_version(self) -> str:
        return self._settings.llm_prompt_version

    def model_for_classify(self) -> str:
        return self._settings.llm_model_classify

    def model_for_default(self) -> str:
        return self._settings.llm_model_default

    def model_for_escalation(self) -> str:
        return self._settings.llm_model_escalation

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def complete_structured(
        self,
        *,
        system: str,
        user_content: str,
        output_format: type[T],
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> StructuredCompletion:
        self._settings.require_api_key()
        response = await self._client.messages.parse(
            model=model or self._settings.llm_model_default,
            max_tokens=max_tokens or self._settings.llm_max_tokens_default,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            output_format=output_format,
        )

        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            explanation = getattr(details, "explanation", None) if details else None
            raise LLMRefusalError(category=category, explanation=explanation)

        parsed = response.parsed_output
        if parsed is None:
            raise StructuredOutputError("model response did not include valid structured output")

        usage = TokenUsage(
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )
        return StructuredCompletion(
            parsed=parsed, usage=usage, model=response.model, prompt_version=self._settings.llm_prompt_version
        )

    async def aclose(self) -> None:
        await self._client.close()
