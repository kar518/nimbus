import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations, salt, expected = hashed_password.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode(), salt.encode(), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str, expires_delta: timedelta | None = None, extra_claims: dict[str, Any] | None = None
) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "kind": "user",
        "exp": datetime.now(UTC)
        + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
    }
    payload.update(extra_claims or {})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "kind"]},
        )
    except jwt.InvalidTokenError:
        return None


def worker_bootstrap_token() -> str:
    return (
        settings.WORKER_API_TOKEN
        or hmac.new(
            settings.SECRET_KEY.encode(), b"nimbus-worker-registration-v1", hashlib.sha256
        ).hexdigest()
    )
