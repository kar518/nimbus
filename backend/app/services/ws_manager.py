"""
WebSocket connection manager and Redis event bridge.

`manager` is a process-wide singleton:

- The `/ws` endpoint (`app.api.v1.endpoints.websocket`) calls
  `manager.connect` / `manager.disconnect` per client connection.
- `manager.redis_bridge` is started once, as a background task in the
  FastAPI `lifespan` (see `app.main`), and runs for the life of the
  process. It subscribes to the same Redis channel that
  `app.services.event_bus.publish_event` publishes to, and rebroadcasts
  every event to all currently-connected WebSocket clients.

This Redis-backed bridge (rather than broadcasting directly from
`publish_event`) is what lets events published from a Celery worker
process reach WebSocket clients connected to the FastAPI process.
"""

import asyncio
import json
from typing import Any

import redis.asyncio as redis
from fastapi import WebSocket

from app.core.config import settings
from app.core.logging import get_logger
from app.services.event_bus import EVENT_CHANNEL

logger = get_logger(__name__)


class ConnectionManager:
    """Tracks connected WebSocket clients and broadcasts messages to them."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send `message` (as JSON) to every connected client.

        Any connection that fails to receive (client gone, socket reset)
        is dropped from the pool rather than raising — one dead client
        should never stop the rest from getting the update.
        """
        async with self._lock:
            connections = list(self._connections)

        if not connections:
            return

        text = json.dumps(message)
        dead: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_text(text)
            except Exception:
                dead.append(connection)

        if dead:
            async with self._lock:
                for connection in dead:
                    self._connections.discard(connection)

    async def redis_bridge(self, stop_event: asyncio.Event) -> None:
        """Subscribe to the shared Redis event channel and rebroadcast to
        all connected WebSocket clients until `stop_event` is set.

        Meant to run as a single long-lived background task for the life
        of the app (started/stopped from `app.main`'s lifespan). Reconnects
        on transient Redis errors instead of taking the whole app down.
        """
        while not stop_event.is_set():
            client: redis.Redis | None = None
            try:
                client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                assert client is not None
                pubsub = client.pubsub()
                await pubsub.subscribe(EVENT_CHANNEL)
                try:
                    while not stop_event.is_set():
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        )
                        if message is None:
                            continue
                        try:
                            data = json.loads(message["data"])
                        except (TypeError, ValueError):
                            logger.warning("ws_manager.bad_event_payload")
                            continue
                        await self.broadcast(data)
                finally:
                    await pubsub.unsubscribe(EVENT_CHANNEL)
                    await pubsub.aclose()  # type: ignore[no-untyped-call]
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("ws_manager.redis_bridge_error", exc_info=True)
                await asyncio.sleep(2)
            finally:
                if client is not None:
                    await client.aclose()


# Process-wide singleton used by both the WebSocket endpoint and the app
# lifespan.
manager = ConnectionManager()
