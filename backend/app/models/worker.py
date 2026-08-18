"""GPU worker ORM model."""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, func
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
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[WorkerStatus] = mapped_column(SAEnum(WorkerStatus, name="worker_status", native_enum=True), default=WorkerStatus.OFFLINE, server_default=WorkerStatus.OFFLINE.value, nullable=False, index=True)
    gpu_memory: Mapped[int] = mapped_column(Integer, nullable=False)
    gpu_utilization: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_job: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
