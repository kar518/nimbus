import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.worker import WorkerStatus

class WorkerCreate(BaseModel):
    name: str
    gpu_memory: int
    gpu_utilization: int = 0

class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    status: WorkerStatus
    gpu_memory: int
    gpu_utilization: int
    current_job: uuid.UUID | None
    last_heartbeat: datetime | None
    created_at: datetime
