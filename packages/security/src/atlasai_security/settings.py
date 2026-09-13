"""Security-related settings, all environment-driven with no in-code
fallback secrets."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class JWTSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="jwt_", extra="ignore")

    signing_key: str
    algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30


class CredentialEncryptionSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    credential_encryption_key: str
