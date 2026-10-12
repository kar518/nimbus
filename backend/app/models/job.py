import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import JSON, Boolean, CheckConstraint, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("priority >= 0", name="ck_jobs_priority_non_negative"),
        CheckConstraint("cpu_request > 0", name="ck_jobs_cpu_request_positive"),
        CheckConstraint("gpu_memory_request >= 0", name="ck_jobs_gpu_memory_request_non_negative"),
        CheckConstraint("estimated_runtime >= 0", name="ck_jobs_estimated_runtime_non_negative"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status"),
        default=JobStatus.QUEUED,
        server_default="QUEUED",
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    worker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    cpu_request: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    gpu_memory_request: Mapped[int] = mapped_column(Integer)
    estimated_runtime: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(
        String(255), default="python:3.12-slim", server_default="python:3.12-slim"
    )
    command: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=512, server_default="512")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, server_default="300")
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    execution_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    exit_code: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    log_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    retry_of: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    assigned_at: Mapped[datetime | None] = mapped_column()
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
