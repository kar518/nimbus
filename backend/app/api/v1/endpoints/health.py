"""
Health and readiness probes.

- `/health`  — liveness: is the process up? Used by Docker HEALTHCHECK.
- `/ready`   — readiness: can the app actually serve traffic (DB + Redis
               reachable)? Used by orchestrators before routing traffic.
"""

from typing import Literal

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: str


class DependencyStatus(BaseModel):
    database: Literal["ok", "unavailable"]
    redis: Literal["ok", "unavailable"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: DependencyStatus


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.ENVIRONMENT)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(response: Response, db: AsyncSession = Depends(get_db)) -> ReadinessResponse:
    db_status: Literal["ok", "unavailable"] = "ok"
    redis_status: Literal["ok", "unavailable"] = "ok"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    try:
        async with redis.Redis.from_url(settings.REDIS_URL) as client:
            await client.ping()
    except Exception:
        redis_status = "unavailable"

    overall = "ready" if db_status == "ok" and redis_status == "ok" else "not_ready"

    if overall == "not_ready":
        response.status_code = 503
    return ReadinessResponse(
        status=overall,
        dependencies=DependencyStatus(database=db_status, redis=redis_status),
    )
