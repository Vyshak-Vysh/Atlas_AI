"""Celery task entrypoints. Bodies are thin — real logic lives in
ingestion/pipeline.py as plain async functions, wrapped here with
`asyncio.run(...)` since Celery invokes task bodies synchronously (see the
implementation plan: "all repositories are async ... Celery tasks wrap
their repository calls with asyncio.run(...) rather than duplicating this
layer as sync code").
"""

from __future__ import annotations

import asyncio
import uuid

from celery import Task
from celery.utils.log import get_task_logger

from ai_atlas.celery_app import celery_app
from ai_atlas.ingestion.pipeline import ingest_source_version
from atlasai_db.engine import dispose_async_engine

logger = get_task_logger(__name__)


async def _ingest_and_dispose(tenant_id: uuid.UUID, source_record_id: uuid.UUID, source_version_id: uuid.UUID) -> int:
    try:
        return await ingest_source_version(
            tenant_id=tenant_id, source_record_id=source_record_id, source_version_id=source_version_id
        )
    finally:
        # See dispose_async_engine's docstring: required because each
        # Celery task body runs asyncio.run() with its own fresh event
        # loop, and the cached async engine's connection pool is bound to
        # whichever loop created it.
        await dispose_async_engine()


def _ingest_source_version_task(
    self: Task, tenant_id: str, source_record_id: str, source_version_id: str
) -> int:
    try:
        return asyncio.run(
            _ingest_and_dispose(
                tenant_id=uuid.UUID(tenant_id),
                source_record_id=uuid.UUID(source_record_id),
                source_version_id=uuid.UUID(source_version_id),
            )
        )
    except Exception as exc:
        logger.exception("ingestion failed for source_version_id=%s", source_version_id)
        raise self.retry(exc=exc) from exc


# Applied as a plain call rather than `@celery_app.task(...)` on the def
# statement — celery ships no type stubs, so the decorator form makes mypy
# flag the whole function as untyped; assigning the wrapped result to a
# module-level name has no such special case.
ingest_source_version_task = celery_app.task(
    name="ai_atlas.ingest_source_version", bind=True, max_retries=3, default_retry_delay=10
)(_ingest_source_version_task)
