"""apps/ai_atlas settings — Celery, embedder client, and agent-run limits.
Every value is environment-driven; nothing here is a fallback secret."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CelerySettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    redis_url: str


class EmbedderClientSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    embedder_base_url: str
    embedding_model_name: str
    embedding_dimension: int = 768


class EmbedderServiceSettings(BaseSettings):
    """Settings for the embedder microservice process itself (as opposed to
    EmbedderClientSettings, used by callers of that service)."""

    model_config = SettingsConfigDict(extra="ignore")

    embedding_model_name: str = "BAAI/bge-base-en-v1.5"
    embedding_dimension: int = 768


class AgentLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="agent_", extra="ignore")

    max_steps: int = 12
    max_calls_per_tool: int = 3
    run_timeout_seconds: int = 180
    tool_timeout_seconds: int = 30
    token_budget: int = 200_000
