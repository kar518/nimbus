import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.worker import WorkerStatus


class WorkerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    gpu_memory: int = Field(default=0, ge=0, le=1048576)
    gpu_utilization: int = Field(default=0, ge=0, le=100)
    cpu_capacity: Decimal = Field(default=Decimal("1"), gt=0, le=1024)
    memory_capacity_mb: int = Field(default=512, ge=64)
    executor: str = Field(default="docker", pattern=r"^docker$")


class Heartbeat(BaseModel):
    gpu_utilization: int = Field(default=0, ge=0, le=100)


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    status: WorkerStatus
    gpu_memory: int
    gpu_utilization: int
    cpu_capacity: Decimal
    memory_capacity_mb: int
    executor: str
    draining: bool
    current_job: uuid.UUID | None
    last_heartbeat: datetime | None
    created_at: datetime


class DrainRequest(BaseModel):
    draining: bool
