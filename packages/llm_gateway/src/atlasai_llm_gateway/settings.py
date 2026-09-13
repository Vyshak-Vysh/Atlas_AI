"""LLM gateway settings. Model IDs are environment-driven, never hardcoded
at a call site — see docs/ADR for why these specific defaults were chosen
(verified against Anthropic's current model catalogue, not recalled from
training data)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AnthropicSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str
    llm_model_classify: str = "claude-haiku-4-5-20251001"
    llm_model_default: str = "claude-sonnet-5"
    llm_model_escalation: str = "claude-opus-5"
    llm_max_tokens_default: int = 8000
    llm_prompt_version: str = "v1"
