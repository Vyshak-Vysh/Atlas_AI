"""Shared async Redis client factory. Used for the realtime agent-step
pub/sub channel (implementation plan §4) by both apps/ai_atlas (publisher)
and apps/api (subscriber/SSE) — Redis is already a hard dependency as the
Celery broker, so this reuses it rather than adding a new subsystem.
"""

from __future__ import annotations

from functools import lru_cache

import redis.asyncio as redis
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    redis_url: str


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = RedisSettings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def agent_run_channel(run_id: str) -> str:
    return f"agent_run:{run_id}:events"
