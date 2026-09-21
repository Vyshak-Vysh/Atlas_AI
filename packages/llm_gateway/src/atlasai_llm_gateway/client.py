"""Google Gemini provider adapter.

Structured outputs use `generate_content` with
`response_mime_type="application/json"` and `response_schema=SomeModel`
-> `response.parsed` — the google-genai SDK's native constrained-decoding
path (verified against the installed SDK, not assumed from training data).
A refusal (blocked prompt, or a candidate that stopped for a safety
reason) is always checked before reading content; retries cover 429/5xx/
transport failures per the SDK's `ClientError`/`ServerError` split.
"""

from __future__ import annotations

from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from atlasai_llm_gateway import _gemini
from atlasai_llm_gateway.cost_tracking import TokenUsage
from atlasai_llm_gateway.settings import GeminiSettings

T = TypeVar("T", bound=BaseModel)


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


class GeminiGateway:
    def __init__(self) -> None:
        self._settings = GeminiSettings()
        # Built on first use: the SDK client cannot exist without a key, and
        # constructing a gateway on a keyless deployment must not fail.
        self._client: genai.Client | None = None

    @property
    def prompt_version(self) -> str:
        return self._settings.llm_prompt_version

    def model_for_classify(self) -> str:
        return self._settings.llm_model_classify

    def model_for_default(self) -> str:
        return self._settings.llm_model_default

    def model_for_escalation(self) -> str:
        return self._settings.llm_model_escalation

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
        resolved_model = model or self._settings.llm_model_default
        response = await self._get_client().aio.models.generate_content(
            model=resolved_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens or self._settings.llm_max_tokens_default,
                response_mime_type="application/json",
                response_schema=output_format,
                # No tools are offered here, but the SDK still treats its
                # automatic function calling as "on" unless told otherwise
                # and logs a warning about it on every worker.
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )

        refused = _gemini.refusal(response)
        if refused is not None:
            category, explanation = refused
            raise LLMRefusalError(category=category, explanation=explanation)

        # The SDK leaves `parsed` unset (rather than raising) when the text
        # is not valid JSON for the schema - typically a MAX_TOKENS cut-off
        # mid-document - so the finish reason is the useful diagnostic here.
        parsed = response.parsed
        if not isinstance(parsed, output_format):
            raise StructuredOutputError(
                "model response did not include valid structured output "
                f"(finish_reason={_gemini.finish_reason_name(response)})"
            )

        usage = _gemini.usage(response, requested_model=resolved_model)
        return StructuredCompletion(
            parsed=parsed, usage=usage, model=usage.model, prompt_version=self._settings.llm_prompt_version
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aio.aclose()
