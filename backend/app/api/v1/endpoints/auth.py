import asyncio
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import admin_user, current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    worker_bootstrap_token,
)
from app.db.session import get_db
from app.models.user import User

router = APIRouter(tags=["authentication"])


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str
    is_admin: bool


def set_session(response: Response, user: User) -> None:
    response.set_cookie(
        "nimbus_session",
        create_access_token(str(user.id)),
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.get("/status")
async def auth_status(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    return {
        "setup_required": (await db.scalar(select(func.count(User.id)))) == 0,
        "requires_setup_token": settings.ENVIRONMENT != "local",
    }


@router.post("/setup", response_model=UserResponse)
async def setup(
    credentials: Credentials,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    if settings.ENVIRONMENT != "local" and (
        not settings.SETUP_TOKEN
        or not hmac.compare_digest(
            request.headers.get("x-nimbus-setup-token", ""), settings.SETUP_TOKEN
        )
    ):
        raise HTTPException(
            403, "A deployment setup token is required to create the first administrator."
        )
    await db.execute(text("SELECT pg_advisory_xact_lock(6472027)"))
    if await db.scalar(select(func.count(User.id))):
        raise HTTPException(409, "Setup is complete. Please sign in.")
    user = User(
        username=credentials.username.lower(),
        password_hash=await asyncio.to_thread(hash_password, credentials.password),
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    set_session(response, user)
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    credentials: Credentials,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    import redis.asyncio as redis

    client = redis.Redis.from_url(settings.REDIS_URL)
    key = "nimbus:login:" + (request.client.host if request.client else "unknown")
    try:
        attempts = await client.incr(key)
        if attempts == 1:
            await client.expire(key, 60)
        if attempts > 10:
            raise HTTPException(429, "Too many sign-in attempts. Try again in one minute.")
    finally:
        await client.aclose()
    user = await db.scalar(select(User).where(User.username == credentials.username.lower()))
    valid = (
        await asyncio.to_thread(verify_password, credentials.password, user.password_hash)
        if user
        else False
    )
    if not user or not valid:
        raise HTTPException(401, "Incorrect username or password.")
    set_session(response, user)
    return user


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("nimbus_session", path="/")
    return {"status": "signed_out"}


@router.post("/users", response_model=UserResponse, status_code=201)
async def add_user(
    credentials: Credentials, _: User = Depends(admin_user), db: AsyncSession = Depends(get_db)
) -> User:
    username = credentials.username.lower()
    if await db.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "That username is already in use.")
    user = User(
        username=username,
        password_hash=await asyncio.to_thread(hash_password, credentials.password),
        is_admin=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/worker-token")
async def worker_token(response: Response, _: User = Depends(admin_user)) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    return {"token": worker_bootstrap_token()}
