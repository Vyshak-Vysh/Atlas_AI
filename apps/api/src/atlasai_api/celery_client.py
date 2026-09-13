"""A lightweight Celery client used only to enqueue tasks by name
(`send_task`) — apps/api never imports apps/ai_atlas's task definitions
directly, keeping the control plane and data plane as separate deployables
that only share the Redis broker, not Python code.
"""

from __future__ import annotations

from functools import lru_cache

from celery import Celery
from pydantic_settings import BaseSettings, SettingsConfigDict


class BrokerSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    redis_url: str


@lru_cache
def get_celery_client() -> Celery:
    settings = BrokerSettings()
    return Celery("atlasai_api_client", broker=settings.redis_url, backend=settings.redis_url)


def enqueue_ingest_source_version(*, tenant_id: str, source_record_id: str, source_version_id: str) -> None:
    get_celery_client().send_task(
        "ai_atlas.ingest_source_version", args=[tenant_id, source_record_id, source_version_id]
    )


def enqueue_run_agent(*, tenant_id: str, project_id: str, agent_run_id: str) -> None:
    get_celery_client().send_task("ai_atlas.run_agent", args=[tenant_id, project_id, agent_run_id])
