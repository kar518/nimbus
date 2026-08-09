"""
`Job` ORM model — a unit of work submitted to Nimbus for scheduling onto
a GPU worker.

Only the schema is defined here. Status transitions, scheduling, and
worker assignment are implemented in `app.services` / `app.workers`, not
on the model itself.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobStatus(str, Enum):
    """Lifecycle states for a submitted job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job(Base):
    """
    A workload submitted for execution.

    `owner_id` and `worker_id` are plain UUID columns (no FK constraint
    yet) because the `User` and `GPUWorker` models don't exist yet. Add
    `ForeignKey` references and relationships once those models land.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("priority >= 0", name="ck_jobs_priority_non_negative"),
        CheckConstraint("cpu_request > 0", name="ck_jobs_cpu_request_positive"),
        CheckConstraint("gpu_memory_request >= 0", name="ck_jobs_gpu_memory_request_non_negative"),
        CheckConstraint("estimated_runtime >= 0", name="ck_jobs_estimated_runtime_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status", native_enum=True),
        default=JobStatus.QUEUED,
        server_default=JobStatus.QUEUED.value,
        nullable=False,
        index=True,
    )

    priority: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    # No FK yet — see class docstring.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Requested resources. CPU is fractional cores (e.g. 2.50); GPU memory
    # is in MB; estimated runtime is in seconds.
    cpu_request: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    gpu_memory_request: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_runtime: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Job id={self.id} title={self.title!r} status={self.status.value}>"
