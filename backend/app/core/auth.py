import hmac
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, worker_bootstrap_token
from app.db.session import get_db
from app.models.user import User


def token_from_request(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    return (
        authorization[7:]
        if authorization.startswith("Bearer ")
        else request.cookies.get("nimbus_session", "")
    )


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    claims = decode_access_token(token_from_request(request))
    try:
        user_id = uuid.UUID(claims["sub"]) if claims and claims.get("kind") == "user" else None
    except (ValueError, KeyError):
        user_id = None
    user = await db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(401, "Please sign in to continue.")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.cookies.get("nimbus_session"):
        from app.core.config import settings

        allowed = {str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS}
        origin = request.headers.get("origin")
        if origin and origin not in allowed:
            raise HTTPException(403, "Request origin is not allowed.")
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Administrator access is required.")
    return user


def registration_auth(request: Request) -> None:
    if not hmac.compare_digest(token_from_request(request), worker_bootstrap_token()):
        raise HTTPException(401, "Invalid worker registration token.")


async def worker_auth(
    request: Request, worker_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    claims = decode_access_token(token_from_request(request))
    if not claims or claims.get("kind") != "worker" or claims.get("sub") != str(worker_id):
        raise HTTPException(401, "Invalid or expired worker credential.")
    from app.models.worker import GPUWorker

    worker = await db.get(GPUWorker, worker_id)
    session = str(worker.session_id) if worker and worker.session_id else None
    if not worker or claims.get("session") != session:
        raise HTTPException(401, "This worker credential was replaced by a new agent session.")
