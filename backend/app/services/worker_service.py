import uuid
from datetime import datetime, timedelta
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.worker import GPUWorker, WorkerStatus
from app.schemas.worker import WorkerCreate
from app.services.event_bus import publish_event

async def create_worker(db: AsyncSession, worker_in: WorkerCreate) -> GPUWorker:
    worker = GPUWorker(name=worker_in.name, gpu_memory=worker_in.gpu_memory, gpu_utilization=worker_in.gpu_utilization)
    db.add(worker); await db.commit(); await db.refresh(worker)
    await publish_event("worker.heartbeat", {"id": str(worker.id), "status": worker.status.value, "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None})
    return worker

async def get_workers(db: AsyncSession) -> list[GPUWorker]:
    result = await db.execute(select(GPUWorker).order_by(GPUWorker.created_at.desc()))
    return list(result.scalars().all())

async def heartbeat_worker(db: AsyncSession, worker_id: uuid.UUID) -> GPUWorker | None:
    result = await db.execute(select(GPUWorker).where(GPUWorker.id == worker_id))
    worker = result.scalar_one_or_none()
    if worker is None: return None
    worker.last_heartbeat = datetime.utcnow()
    if worker.status == WorkerStatus.OFFLINE: worker.status = WorkerStatus.IDLE
    await db.commit(); await db.refresh(worker)
    await publish_event("worker.heartbeat", {"id": str(worker.id), "status": worker.status.value, "last_heartbeat": worker.last_heartbeat.isoformat()})
    return worker

async def mark_stale_workers_offline(db: AsyncSession) -> list[GPUWorker]:
    """Flip any non-OFFLINE worker whose heartbeat has gone stale (or who
    has never sent one) to OFFLINE, and publish a `worker.status` event for
    each so the dashboard reflects it live.

    This is the actual "online/offline detection" — without it, a worker
    that stops heartbeating just gets silently skipped by the scheduler
    while its `status` field keeps reading IDLE/BUSY forever. Called from
    `app.services.scheduler_service.run_scheduling_cycle`, which already
    runs on `SCHEDULER_POLL_INTERVAL_SECONDS`, so this piggybacks on that
    cadence instead of needing a separate polling loop.

    A worker that goes stale while BUSY (mid-job) is marked OFFLINE too;
    `app.workers.tasks.execution._release_worker` already knows not to
    reset an OFFLINE worker back to IDLE when its job finishes.
    """
    stale_cutoff = datetime.utcnow() - timedelta(seconds=settings.WORKER_HEARTBEAT_TIMEOUT_SECONDS)
    result = await db.execute(
        select(GPUWorker).where(
            GPUWorker.status != WorkerStatus.OFFLINE,
            or_(GPUWorker.last_heartbeat.is_(None), GPUWorker.last_heartbeat < stale_cutoff),
        )
    )
    stale_workers = list(result.scalars().all())
    if not stale_workers:
        return []

    for worker in stale_workers:
        worker.status = WorkerStatus.OFFLINE
    await db.commit()

    for worker in stale_workers:
        await db.refresh(worker)
        await publish_event(
            "worker.status",
            {
                "id": str(worker.id),
                "status": worker.status.value,
                "current_job": str(worker.current_job) if worker.current_job else None,
            },
        )

    return stale_workers
