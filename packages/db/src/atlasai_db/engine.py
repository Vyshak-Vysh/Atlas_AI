"""Engine/session factories.

Two engines are exposed deliberately: an async engine (asyncpg) for
apps/api's request/response path, and a sync engine (psycopg 3) for
apps/ai_atlas's Celery tasks, which are sync by default. Both bind the same
`Base.metadata`. Alembic's env.py also imports `Base.metadata` from here.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from atlasai_db.settings import DatabaseSettings


@lru_cache
def get_async_engine() -> AsyncEngine:
    settings = DatabaseSettings()
    return create_async_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_sync_engine() -> Engine:
    settings = DatabaseSettings()
    return create_engine(settings.database_url_sync, pool_pre_ping=True)


@lru_cache
def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_async_engine(), expire_on_commit=False)


@lru_cache
def get_sync_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_sync_engine(), expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: `Depends(get_async_session)`."""
    session_factory = get_async_sessionmaker()
    async with session_factory() as session:
        yield session


async def dispose_async_engine() -> None:
    """Must be called at the end of every `asyncio.run(...)`-wrapped Celery
    task body that used the async engine (apps/ai_atlas), in a `finally`
    block — NOT from apps/api, which keeps one engine for uvicorn's whole
    process lifetime.

    `get_async_engine()` is a process-wide `@lru_cache`'d singleton, but
    each `asyncio.run(...)` call creates and destroys its own event loop,
    and asyncpg's pooled connections are bound to the loop that created
    them. Without this, a second Celery task in the same worker process
    reuses the first task's now-closed-loop connection pool and fails with
    "Future attached to a different loop". Disposing the pool and clearing
    the cache forces the next task to build a fresh engine under its own
    new loop.
    """
    engine = get_async_engine()
    await engine.dispose()
    get_async_engine.cache_clear()
    get_async_sessionmaker.cache_clear()


def get_sync_session() -> Generator[Session, None, None]:
    """Celery task usage: `with get_sync_session() as session: ...` via
    contextlib, or iterate the generator directly in a `for` loop of one."""
    session_factory = get_sync_sessionmaker()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
