import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job import TERMINAL_STATUSES, Job, JobStatus
from app.models.worker import GPUWorker, WorkerStatus
from app.schemas.worker import WorkerCreate
from app.services.event_bus import publish_event
from app.services.job_service import now, transition_lock


async def create_worker(db: AsyncSession, worker_in: WorkerCreate) -> GPUWorker:
    await transition_lock(db)
    worker = await db.scalar(select(GPUWorker).where(GPUWorker.name == worker_in.name))
    cutoff = now() - timedelta(seconds=settings.WORKER_HEARTBEAT_TIMEOUT_SECONDS)
    if worker:
        if (
            worker.status != WorkerStatus.OFFLINE
            and worker.last_heartbeat
            and worker.last_heartbeat >= cutoff
        ):
            raise HTTPException(
                409,
                "An agent with this name is already online. Choose another name or stop it first.",
            )
        if worker.current_job:
            job = await db.get(Job, worker.current_job)
            if job and job.status not in TERMINAL_STATUSES:
                job.status = JobStatus.CANCELLED if job.cancel_requested else JobStatus.FAILED
                job.completed_at = now()
                job.failure_reason = "Worker agent restarted before reporting an outcome."
        for key, value in worker_in.model_dump().items():
            setattr(worker, key, value)
    else:
        worker = GPUWorker(**worker_in.model_dump())
        db.add(worker)
    worker.session_id = uuid.uuid4()
    worker.status = WorkerStatus.IDLE
    worker.current_job = None
    worker.last_heartbeat = now()
    await db.commit()
    await db.refresh(worker)
    await publish_event("worker.status", {"id": str(worker.id)})
    return worker


async def get_workers(db: AsyncSession) -> list[GPUWorker]:
    return list((await db.scalars(select(GPUWorker).order_by(GPUWorker.created_at.desc()))).all())


async def heartbeat_worker(
    db: AsyncSession, worker_id: uuid.UUID, utilization: int = 0
) -> GPUWorker:
    await transition_lock(db)
    worker = await db.get(GPUWorker, worker_id)
    if not worker:
        raise HTTPException(404, "Worker not found.")
    worker.last_heartbeat = now()
    worker.gpu_utilization = utilization
    if worker.status == WorkerStatus.OFFLINE:
        worker.status = WorkerStatus.BUSY if worker.current_job else WorkerStatus.IDLE
    await db.commit()
    await publish_event("worker.heartbeat", {"id": str(worker.id)})
    return worker


async def mark_stale_workers_offline(db: AsyncSession) -> list[GPUWorker]:
    cutoff = now() - timedelta(seconds=settings.WORKER_HEARTBEAT_TIMEOUT_SECONDS)
    stale = list(
        (
            await db.scalars(
                select(GPUWorker).where(
                    GPUWorker.status != WorkerStatus.OFFLINE, GPUWorker.last_heartbeat < cutoff
                )
            )
        ).all()
    )
    for worker in stale:
        worker.status = WorkerStatus.OFFLINE
        if worker.current_job:
            job = await db.get(Job, worker.current_job)
            if job and job.status not in TERMINAL_STATUSES:
                job.status = JobStatus.CANCELLED if job.cancel_requested else JobStatus.FAILED
                job.completed_at = now()
                job.failure_reason = "Worker heartbeat expired. Check the agent before retrying."
            worker.current_job = None
    return stale
