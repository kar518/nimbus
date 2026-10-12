import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job import Job, JobStatus
from app.models.worker import GPUWorker, WorkerStatus
from app.services.event_bus import publish_event
from app.services.job_service import now, transition_lock
from app.services.worker_service import mark_stale_workers_offline


async def run_scheduling_cycle(db: AsyncSession) -> list[Job]:
    await transition_lock(db)
    stale = await mark_stale_workers_offline(db)
    assigned = list((await db.scalars(select(Job).where(Job.status == JobStatus.ASSIGNED))).all())
    for job in assigned:
        if job.assigned_at and job.assigned_at < now() - timedelta(seconds=60):
            worker = await db.get(GPUWorker, job.worker_id)
            if worker:
                worker.status = WorkerStatus.OFFLINE
                worker.current_job = None
            job.status = JobStatus.FAILED
            job.completed_at = now()
            job.failure_reason = "Worker did not claim this assignment within 60 seconds."
    running = list((await db.scalars(select(Job).where(Job.status == JobStatus.RUNNING))).all())
    for job in running:
        if job.started_at and job.started_at < now() - timedelta(seconds=job.timeout_seconds + 120):
            worker = await db.get(GPUWorker, job.worker_id)
            if worker:
                worker.status = WorkerStatus.OFFLINE
                worker.current_job = None
            job.status = JobStatus.FAILED
            job.completed_at = now()
            job.failure_reason = "Execution exceeded its timeout and recovery grace period."
    cutoff = now() - timedelta(seconds=settings.WORKER_HEARTBEAT_TIMEOUT_SECONDS)
    workers = list(
        (
            await db.scalars(
                select(GPUWorker)
                .where(
                    GPUWorker.status == WorkerStatus.IDLE,
                    GPUWorker.current_job.is_(None),
                    GPUWorker.last_heartbeat >= cutoff,
                    GPUWorker.executor == "docker",
                    GPUWorker.draining.is_(False),
                )
                .order_by(GPUWorker.gpu_memory, GPUWorker.cpu_capacity)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    queued = list(
        (
            await db.scalars(
                select(Job)
                .where(Job.status == JobStatus.QUEUED)
                .order_by(Job.priority.desc(), Job.created_at)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    newly_assigned = []
    for job in queued:
        candidate = next(
            (
                worker
                for worker in workers
                if worker.gpu_memory >= job.gpu_memory_request
                and worker.cpu_capacity >= job.cpu_request
                and worker.memory_capacity_mb >= job.memory_limit_mb
            ),
            None,
        )
        if not candidate or not job.command:
            continue
        workers.remove(candidate)
        candidate.status = WorkerStatus.BUSY
        candidate.current_job = job.id
        job.worker_id = candidate.id
        job.status = JobStatus.ASSIGNED
        job.assigned_at = now()
        job.execution_token = uuid.uuid4()
        newly_assigned.append(job)
    await db.commit()
    if stale or newly_assigned or assigned or running:
        await publish_event("cluster.updated", {})
    return newly_assigned


async def waiting_reason(db: AsyncSession, job: Job) -> str | None:
    if job.status != JobStatus.QUEUED:
        return None
    if not job.command:
        return "This legacy job has no executable command. Submit a new workload."
    cutoff = now() - timedelta(seconds=settings.WORKER_HEARTBEAT_TIMEOUT_SECONDS)
    workers = list(
        (
            await db.scalars(
                select(GPUWorker).where(
                    GPUWorker.executor == "docker",
                    GPUWorker.last_heartbeat >= cutoff,
                    GPUWorker.status != WorkerStatus.OFFLINE,
                    GPUWorker.draining.is_(False),
                )
            )
        ).all()
    )
    if not workers:
        return "Waiting for an online execution worker."
    suitable = [
        w
        for w in workers
        if w.gpu_memory >= job.gpu_memory_request
        and w.cpu_capacity >= job.cpu_request
        and w.memory_capacity_mb >= job.memory_limit_mb
    ]
    if not suitable:
        return "No online worker has enough requested CPU, RAM, and GPU memory."
    if all(w.status == WorkerStatus.BUSY for w in suitable):
        return "Compatible workers are busy. This job will run when capacity is available."
    return "Ready for the next scheduling cycle."
