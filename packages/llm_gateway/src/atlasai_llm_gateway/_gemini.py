"""Shared Gemini protocol plumbing for `client.py` and `tool_loop.py`.

Both gateways speak to the same `generate_content` endpoint and need the
same three translations, so they live here once:

*   which SDK exceptions are worth retrying (429 and 5xx, plus transport
    failures that never reached the API),
*   how the provider signals "the model declined" - Gemini has no single
    refusal stop reason; a blocked prompt arrives as `prompt_feedback`
    with no candidates at all, while a blocked response arrives as a
    candidate whose `finish_reason` is one of the safety values,
*   how the provider's usage metadata maps onto `TokenUsage`.
"""

from __future__ import annotations

import httpx
from google import genai
from google.genai import errors, types

from atlasai_llm_gateway.cost_tracking import TokenUsage
from atlasai_llm_gateway.settings import GeminiSettings

# Candidate finish reasons that mean the model (or the provider's policy
# layer) declined to answer, rather than finished or ran out of budget.
_REFUSAL_FINISH_REASONS = frozenset(
    {
        types.FinishReason.SAFETY,
        types.FinishReason.RECITATION,
        types.FinishReason.BLOCKLIST,
        types.FinishReason.PROHIBITED_CONTENT,
        types.FinishReason.SPII,
        types.FinishReason.IMAGE_SAFETY,
        types.FinishReason.IMAGE_PROHIBITED_CONTENT,
        types.FinishReason.IMAGE_RECITATION,
    }
)


def is_retryable(exc: BaseException) -> bool:
    """Retry on rate limiting, provider-side failures, and connection-level
    errors. Every other 4xx (bad request, invalid key, model not found) is
    a caller bug that retrying would only repeat."""
    if isinstance(exc, errors.ServerError):
        return True
    if isinstance(exc, errors.ClientError):
        return exc.code == 429
    return isinstance(exc, httpx.TransportError)


def build_client(settings: GeminiSettings) -> genai.Client:
    """`genai.Client` refuses to construct without a key, so gateways build
    it lazily - right before the first request - after `require_api_key()`
    has had the chance to raise the actionable error instead."""
    return genai.Client(api_key=settings.require_api_key())


def first_candidate(response: types.GenerateContentResponse) -> types.Candidate | None:
    if not response.candidates:
        return None
    return response.candidates[0]


def refusal(response: types.GenerateContentResponse) -> tuple[str | None, str | None] | None:
    """Return `(category, explanation)` when the response is a refusal,
    else `None`. Checked before any content is read so a refusal can never
    be mistaken for an empty answer."""
    feedback = response.prompt_feedback
    if feedback is not None and feedback.block_reason is not None:
        return feedback.block_reason.name, feedback.block_reason_message

    candidate = first_candidate(response)
    reason = candidate.finish_reason if candidate is not None else None
    if candidate is not None and reason is not None and reason in _REFUSAL_FINISH_REASONS:
        return reason.name, candidate.finish_message
    return None


def finish_reason_name(response: types.GenerateContentResponse) -> str | None:
    candidate = first_candidate(response)
    if candidate is None or candidate.finish_reason is None:
        return None
    return candidate.finish_reason.name


def usage(response: types.GenerateContentResponse, *, requested_model: str) -> TokenUsage:
    """Gemini bills a thinking model's reasoning tokens as output, so they
    are folded into `output_tokens` here; otherwise the per-run token
    budget and the cost figure would both under-count every 3.x call."""
    meta = response.usage_metadata
    if meta is None:
        return TokenUsage(model=response.model_version or requested_model, input_tokens=0, output_tokens=0)
    return TokenUsage(
        model=response.model_version or requested_model,
        input_tokens=meta.prompt_token_count or 0,
        output_tokens=(meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0),
        cache_read_input_tokens=meta.cached_content_token_count or 0,
    )
