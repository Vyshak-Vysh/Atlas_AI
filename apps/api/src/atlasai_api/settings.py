"""apps/api application settings. Every value is environment-driven — no
secrets or environment-specific values are hardcoded here."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="atlasai_", extra="ignore")

    env: str = "development"
    log_level: str = "INFO"


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    api_cors_allow_origins: str = "http://localhost:3000"

    @property
    def allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_allow_origins.split(",") if origin.strip()]
