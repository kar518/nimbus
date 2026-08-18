"""
WebSocket endpoint for live dashboard updates.

Clients connect to `/ws` (mounted under `settings.API_V1_PREFIX`, so
`/api/v1/ws`) and receive every event published via
`app.services.event_bus.publish_event` — worker heartbeats, worker status
changes, job assignment, and job status changes — relayed through
`app.services.ws_manager.manager`.

No prefix is applied to this router in `app.api.v1.router` (unlike
`jobs`/`workers`) so the path is exactly `/ws`, matching
`VITE_WS_BASE_URL` + `/ws` on the frontend.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.ws_manager import manager

router = APIRouter(tags=["websocket"])
logger = get_logger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Register the client, then block until it disconnects.

    Clients aren't expected to send anything — this is a broadcast-only
    channel — but we still need to `receive` in a loop so the server
    notices when the client goes away.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("websocket.connection_error", exc_info=True)
    finally:
        await manager.disconnect(websocket)
