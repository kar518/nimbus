"""
Pydantic schemas for `Job`.

`JobCreate` is intentionally narrow: it only exposes fields a client is
allowed to set at submission time. Server-managed fields (id, status,
worker_id, timestamps) are never accepted from the client — they're
assigned by the service layer / scheduler.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobStatus


class JobCreate(BaseModel):
    """Fields a client may submit when creating a job."""

    title: str = Field(min_length=1, max_length=255)
    priority: int = Field(default=0, ge=0)
    owner_id: uuid.UUID | None = None
    cpu_request: Decimal = Field(gt=0, decimal_places=2)
    gpu_memory_request: int = Field(ge=0)
    estimated_runtime: int = Field(ge=0)


class JobResponse(BaseModel):
    """Public representation of a job returned by the API."""

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
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
