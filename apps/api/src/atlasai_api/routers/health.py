from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from atlasai_db.engine import get_async_engine

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — process is up. No dependency checks."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, str]:
    """Readiness — can this instance actually serve traffic."""
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — readiness must never raise, only report
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "detail": str(exc)}
    return {"status": "ready"}
