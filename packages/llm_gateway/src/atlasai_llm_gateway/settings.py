"""LLM gateway settings. Model IDs are environment-driven, never hardcoded
at a call site — see docs/ADR for why these specific defaults were chosen
(verified against Google's current Gemini model catalogue, not recalled
from training data)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingAPIKeyError(RuntimeError):
    """Raised when a model call is attempted with no API key configured.

    The provider SDK's own message for this is "No API key was provided.
    Please pass a valid API key", raised from `genai.Client(...)` at
    construction time, which surfaces on an agent run as an opaque FAILED
    status that looks like a bug in the pipeline rather than a missing line
    in `.env`. This says what to actually do instead.
    """

    def __init__(self) -> None:
        super().__init__(
            "GEMINI_API_KEY is not set, so the agent cannot call a model. "
            "Add it to .env and restart the worker (`docker compose up -d ai_atlas_worker`). "
            "Everything that does not need a model - ingestion, retrieval, and the whole "
            "API surface - works without it."
        )


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    gemini_api_key: str = ""
    """Empty is allowed at construction so that importing or wiring up a
    gateway never fails on a deployment that has not configured a key;
    `require_api_key()` is what guards an actual model call. The variable
    name matches the one the google-genai SDK itself reads, so a key set
    for other Gemini tooling on the same host is picked up unchanged."""

    llm_model_classify: str = "gemini-3.5-flash-lite"
    llm_model_default: str = "gemini-3.8-flash"
    llm_model_escalation: str = "gemini-3.1-pro-preview"
    llm_max_tokens_default: int = 8000
    llm_prompt_version: str = "v1"

    def require_api_key(self) -> str:
        """Call immediately before a request. Raises `MissingAPIKeyError`
        rather than letting the SDK fail with a message that does not name
        the variable to set."""
        key = self.gemini_api_key.strip()
        if not key:
            raise MissingAPIKeyError
        return key
