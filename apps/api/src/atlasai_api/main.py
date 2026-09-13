"""AtlasAI FastAPI control plane entrypoint.

Every endpoint here authenticates the user, resolves tenant/project
context, and (for sensitive actions) records an audit event — per
ATLASAI_MASTER_SPEC.md §10. Tables are never auto-created here; the
database is expected to already be migrated (`alembic upgrade head`)
before this app starts.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlasai_api.logging import configure_logging, get_logger
from atlasai_api.middleware import RequestIDMiddleware
from atlasai_api.routers import (
    actions,
    agent,
    audit,
    auth,
    connectors,
    documents,
    evidence,
    findings,
    health,
    projects,
    reports,
    requirements,
    sources,
    tenants,
    users,
)
from atlasai_api.settings import CORSSettings

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    logger.info("atlasai_api.startup")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AtlasAI API",
        description="Evidence-backed enterprise project intelligence platform — control plane.",
        version="0.1.0",
        lifespan=_lifespan,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORSSettings().allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(tenants.router)
    app.include_router(projects.router)
    app.include_router(documents.router)
    app.include_router(sources.router)
    app.include_router(evidence.router)
    app.include_router(agent.router)
    app.include_router(findings.router)
    app.include_router(actions.router)
    app.include_router(audit.router)
    app.include_router(connectors.router)
    app.include_router(requirements.router)
    app.include_router(reports.router)

    return app


app = create_app()
