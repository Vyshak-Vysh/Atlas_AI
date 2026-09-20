"""LLM gateway settings. Model IDs are environment-driven, never hardcoded
at a call site — see docs/ADR for why these specific defaults were chosen
(verified against Anthropic's current model catalogue, not recalled from
training data)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class MissingAPIKeyError(RuntimeError):
    """Raised when a model call is attempted with no API key configured.

    The provider SDK's own message for this is "Could not resolve
    authentication method. Expected one of api_key, auth_token, or
    credentials to be set", which surfaces on an agent run as an opaque
    FAILED status that looks like a bug in the pipeline rather than a
    missing line in `.env`. This says what to actually do instead.
    """

    def __init__(self) -> None:
        super().__init__(
            "ANTHROPIC_API_KEY is not set, so the agent cannot call a model. "
            "Add it to .env and restart the worker (`docker compose up -d ai_atlas_worker`). "
            "Everything that does not need a model - ingestion, retrieval, and the whole "
            "API surface - works without it."
        )


class AnthropicSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str = ""
    """Empty is allowed at construction so that importing or wiring up a
    gateway never fails on a deployment that has not configured a key;
    `require_api_key()` is what guards an actual model call."""

    llm_model_classify: str = "claude-haiku-4-5-20251001"
    llm_model_default: str = "claude-sonnet-5"
    llm_model_escalation: str = "claude-opus-5"
    llm_max_tokens_default: int = 8000
    llm_prompt_version: str = "v1"

    def require_api_key(self) -> str:
        """Call immediately before a request. Raises `MissingAPIKeyError`
        rather than letting the SDK fail with a message that does not name
        the variable to set."""
        key = self.anthropic_api_key.strip()
        if not key:
            raise MissingAPIKeyError
        return key
