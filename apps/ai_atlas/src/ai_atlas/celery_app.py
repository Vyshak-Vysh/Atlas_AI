"""Celery application. Broker and result backend are the same Redis
instance used for realtime pub/sub (see the implementation plan's
"Realtime" section) — one fewer moving part than a separate message queue.
"""

from __future__ import annotations

from celery import Celery

from ai_atlas.settings import CelerySettings

_settings = CelerySettings()

celery_app = Celery(
    "ai_atlas",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=[
        "ai_atlas.ingestion.tasks",
        "ai_atlas.agent_runner.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
