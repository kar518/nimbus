import base64
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.job import JobStatus

DEFAULT_COMMAND = [
    "python",
    "-u",
    "-c",
    (
        "import time; print('Nimbus worker ready', flush=True); "
        "[(print(f'Step {i+1}/5 complete', flush=True), time.sleep(1)) for i in range(5)]; "
        "print('Workload completed successfully', flush=True)"
    ),
]


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)
    priority: int = Field(default=0, ge=0, le=100)
    cpu_request: Decimal = Field(default=Decimal("1"), gt=0, le=128, decimal_places=2)
    gpu_memory_request: int = Field(default=0, ge=0, le=1048576)
    estimated_runtime: int = Field(default=0, ge=0)
    image: str = Field(
        default="python:3.12-slim",
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._/:@-]*$",
    )
    command: list[str] = Field(
        default_factory=lambda: list(DEFAULT_COMMAND), min_length=1, max_length=64
    )
    memory_limit_mb: int = Field(default=512, ge=64, le=65536)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)

    @field_validator("title")
    @classmethod
    def valid_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Give this job a name.")
        return value.strip()

    @field_validator("command")
    @classmethod
    def valid_command(cls, value: list[str]) -> list[str]:
        if not value[0] or any(len(arg) > 16384 or "\x00" in arg for arg in value):
            raise ValueError("Command arguments must be valid and at most 16 KB each.")
        return value


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    status: JobStatus
    priority: int
    owner_id: uuid.UUID | None
    worker_id: uuid.UUID | None
    cpu_request: Decimal
    gpu_memory_request: int
    estimated_runtime: int
    image: str
    command: list[str]
    memory_limit_mb: int
    timeout_seconds: int
    cancel_requested: bool
    exit_code: int | None
    failure_reason: str | None
    retry_of: uuid.UUID | None
    created_at: datetime
    assigned_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    waiting_reason: str | None = None


class ExecutionLease(BaseModel):
    execution_token: uuid.UUID


class LogAppend(ExecutionLease):
    offset: int = Field(ge=0)
    text: str = Field(max_length=16384)


class ArtifactUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    content_base64: str = Field(max_length=2_800_000)

    @field_validator("content_base64")
    @classmethod
    def valid_content(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError("Artifact must be base64 encoded.") from exc
        if len(decoded) > 2 * 1024 * 1024:
            raise ValueError("Each artifact may be at most 2 MB.")
        return value


class ExecutionResult(ExecutionLease):
    exit_code: int
    reason: str | None = Field(default=None, max_length=2000)
    artifacts: list[ArtifactUpload] = Field(default_factory=list, max_length=8)
