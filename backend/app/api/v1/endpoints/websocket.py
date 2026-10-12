from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.security import decode_access_token
from app.services.ws_manager import manager

router = APIRouter(tags=["live updates"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    allowed = {str(value).rstrip("/") for value in settings.BACKEND_CORS_ORIGINS}
    claims = decode_access_token(websocket.cookies.get("nimbus_session", ""))
    if not claims or claims.get("kind") != "user" or (origin and origin not in allowed):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
