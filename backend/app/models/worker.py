import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkerStatus(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class GPUWorker(Base):
    __tablename__ = "workers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[WorkerStatus] = mapped_column(
        SAEnum(WorkerStatus, name="worker_status"),
        default=WorkerStatus.OFFLINE,
        server_default="OFFLINE",
        index=True,
    )
    gpu_memory: Mapped[int] = mapped_column(Integer)
    gpu_utilization: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cpu_capacity: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=1, server_default="1")
    memory_capacity_mb: Mapped[int] = mapped_column(Integer, default=512, server_default="512")
    executor: Mapped[str] = mapped_column(String(32), default="legacy", server_default="legacy")
    draining: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    current_job: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
