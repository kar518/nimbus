"""
Application configuration.

All runtime configuration is sourced from environment variables (see
`.env.example` at the repo root). Nothing here should be hardcoded for a
specific environment — local, staging, and production all use this same
Settings class with different environment values injected by Docker Compose
or the deployment platform.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    PROJECT_NAME: str = "Nimbus"
    ENVIRONMENT: Literal["local", "test", "staging", "production"] = "local"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Security ---
    SECRET_KEY: str = Field(..., description="Used to sign JWTs. Must be set via env var.")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # --- CORS ---
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # --- Database ---
    POSTGRES_USER: str = "nimbus"
    POSTGRES_PASSWORD: str = "nimbus"
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "nimbus"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @property
    def SQLALCHEMY_SYNC_DATABASE_URI(self) -> str:
        """Sync URI used by Alembic migrations."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg2",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    # --- Redis / Celery ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_DEFAULT_QUEUE: str = "nimbus.default"

    @field_validator("CELERY_BROKER_URL", mode="after")
    @classmethod
    def default_broker_url(cls, v: str | None, info) -> str:  # noqa: ANN001
        if v:
            return v
        redis_host = info.data.get("REDIS_HOST", "redis")
        redis_port = info.data.get("REDIS_PORT", 6379)
        redis_db = info.data.get("REDIS_DB", 0)
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

    @field_validator("CELERY_RESULT_BACKEND", mode="after")
    @classmethod
    def default_result_backend(cls, v: str | None, info) -> str:  # noqa: ANN001
        if v:
            return v
        redis_host = info.data.get("REDIS_HOST", "redis")
        redis_port = info.data.get("REDIS_PORT", 6379)
        redis_db = info.data.get("REDIS_DB", 0)
        return f"redis://{redis_host}:{redis_port}/{redis_db}"

    # --- GPU worker / scheduler (placeholders for future config, no logic yet) ---
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = 15
    WORKER_HEARTBEAT_TIMEOUT_SECONDS: int = 45
    SCHEDULER_POLL_INTERVAL_SECONDS: int = 5


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor.

    Use as a FastAPI dependency (`Depends(get_settings)`) or call directly
    in non-request contexts (Celery tasks, scripts). Cached so environment
    parsing only happens once per process.
    """
    return Settings()


settings = get_settings()
