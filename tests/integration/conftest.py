"""Integration test fixtures — a real ASGI client against the actual
FastAPI app, backed by the real (dockerized) Postgres/Redis instance
pointed to by .env. No mocks: these tests exercise the same code path a
production request would (TD_v2.md's own "no arbitrary SQL" and "treat
retrieved content as untrusted" rules are only meaningfully tested this
way, not through mocked repositories).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from atlasai_api.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@atlasai-integration-tests.dev"
