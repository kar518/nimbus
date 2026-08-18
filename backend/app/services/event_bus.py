"""
Event bus: a thin pub/sub wrapper around Redis.

This decouples event producers (services like `worker_service`/`job_service`,
Celery tasks like `scheduling`/`execution`) from event consumers (the
WebSocket connection manager in `app.services.ws_manager`). Producers call
`publish_event`; `ws_manager.redis_bridge` subscribes to `EVENT_CHANNEL` and
fans messages out to connected WebSocket clients.

Using Redis (rather than an in-process channel) means events published from
a Celery worker process reach WebSocket clients connected to a *different*
FastAPI/uvicorn process — which is required given `backend` and
`celery-worker` are separate containers/processes in docker-compose.
"""

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Shared pub/sub channel for all Nimbus domain events (worker heartbeats,
# worker status changes, job assignment, job status changes, ...).
EVENT_CHANNEL = "nimbus:events"

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Lazily create and cache a module-level Redis client.

    Lazy so importing this module never opens a connection (e.g. during
    tests that never publish an event), and cached so repeated publishes
    don't pay connection setup cost each time.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def publish_event(event_type: str, payload: dict[str, Any]) -> None:
    """Publish a domain event onto the shared Redis channel.

    `event_type` is a dotted name such as `"worker.heartbeat"`,
    `"worker.status"`, `"job.assigned"`, or `"job.status"`. `payload` is
    whatever JSON-serializable data subscribers need (ids, new status,
    etc).

    Publishing failures are logged and swallowed rather than raised —
    a Redis blip should never fail the request or task that triggered the
    event (e.g. a worker heartbeat write must succeed even if nobody is
    currently listening on the WebSocket channel).
    """
    message = json.dumps({"type": event_type, "payload": payload})
    try:
        client = get_redis_client()
        await client.publish(EVENT_CHANNEL, message)
    except Exception:
        logger.warning("event_bus.publish_failed", event_type=event_type, exc_info=True)
