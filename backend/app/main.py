"""
Nimbus API entrypoint.

Run locally with:
    uvicorn app.main:app --reload

Run in a container via the `development` or `production` Dockerfile stage
(see docker-compose.yml).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.services.ws_manager import manager

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("nimbus.startup", environment=settings.ENVIRONMENT)
    stop_event = asyncio.Event()
    bridge = asyncio.create_task(manager.redis_bridge(stop_event))
    try:
        yield
    finally:
        stop_event.set(); bridge.cancel(); await asyncio.gather(bridge, return_exceptions=True)
        logger.info("nimbus.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI Workload Scheduling and GPU Resource Management Platform",
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
