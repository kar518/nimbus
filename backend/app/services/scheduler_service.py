"""
Scheduler service layer.

Holds the actual scheduling business logic — finding queued jobs, picking
eligible workers, and assigning them — as a plain async function over an
`AsyncSession`, following the same pattern as `job_service`/`worker_service`.

`app.workers.tasks.scheduling` (the Celery task invoked by Celery beat) is
a thin wrapper around `run_scheduling_cycle`: it just owns the sync/async
boundary (`asyncio.run`) and the session lifecycle, the same way API
endpoints own the HTTP boundary around `job_service`/`worker_service`.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job import Job, JobStatus
from app.models.worker import GPUWorker, WorkerStatus
from app.services.event_bus import publish_event
from app.services.worker_service import mark_stale_workers_offline


async def get_eligible_workers(db: AsyncSession) -> list[GPUWorker]:
    """Workers that can currently be assigned a job.

    Eligible means: IDLE, not already holding a job, and "online" — a
    heartbeat within `WORKER_HEARTBEAT_TIMEOUT_SECONDS`. Stale/offline
    workers (no recent heartbeat, or explicitly OFFLINE) are excluded
    entirely rather than merely deprioritized.
    """
    stale_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        seconds=settings.WORKER_HEARTBEAT_TIMEOUT_SECONDS
    )
    result = await db.execute(
        select(GPUWorker)
        .where(
            GPUWorker.status == WorkerStatus.IDLE,
            GPUWorker.current_job.is_(None),
            GPUWorker.last_heartbeat.is_not(None),
            GPUWorker.last_heartbeat >= stale_cutoff,
        )
        .order_by(GPUWorker.gpu_memory.asc())
    )
    return list(result.scalars().all())


async def get_queued_jobs(db: AsyncSession) -> list[Job]:
    """Queued jobs in scheduling order: highest priority first, then
    oldest first within a priority tier."""
    result = await db.execute(
        select(Job)
        .where(Job.status == JobStatus.QUEUED)
        .order_by(Job.priority.desc(), Job.created_at.asc())
    )
    return list(result.scalars().all())


async def assign_job_to_worker(db: AsyncSession, job: Job, candidate: GPUWorker) -> GPUWorker | None:
    """Attempt to assign `job` to `candidate`, guarding against a
    concurrent assignment.

    Re-selects the worker with a row lock (`SELECT ... FOR UPDATE
    SKIP LOCKED`) and re-checks `status == IDLE` immediately before
    writing, so a concurrent scheduler run (or a heartbeat/execution
    update racing this one) can never double-assign the same worker.
    Returns the locked worker on success, or `None` if it was already
    claimed elsewhere between the caller's SELECT and this call —
    callers should treat that as "try a different worker."
    """
    lock_result = await db.execute(
        select(GPUWorker)
        .where(GPUWorker.id == candidate.id, GPUWorker.status == WorkerStatus.IDLE)
        .with_for_update(skip_locked=True)
    )
    worker = lock_result.scalar_one_or_none()
    if worker is None:
        return None

    worker.status = WorkerStatus.BUSY
    worker.current_job = job.id
    job.worker_id = worker.id
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(job)
    await db.refresh(worker)

    await publish_event(
        "job.assigned",
        {
            "id": str(job.id),
            "job_id": str(job.id),
            "worker_id": str(worker.id),
            "status": job.status.value,
        },
    )
    await publish_event(
        "worker.status",
        {
            "id": str(worker.id),
            "status": worker.status.value,
            "current_job": str(job.id),
        },
    )

    return worker


async def run_scheduling_cycle(db: AsyncSession) -> list[Job]:
    """Assign as many queued jobs to eligible workers as possible in one
    pass. Returns the jobs that were assigned this cycle (callers are
    responsible for handing each off to `nimbus.jobs.execute`).
    """
    # Online/offline detection piggybacks on this same cadence — see
    # `mark_stale_workers_offline` for why it lives here.
    await mark_stale_workers_offline(db)

    queued_jobs = await get_queued_jobs(db)
    if not queued_jobs:
        return []

    eligible_workers = await get_eligible_workers(db)
    newly_assigned: list[Job] = []

    for job in queued_jobs:
        if not eligible_workers:
            break

        candidate = next(
            (w for w in eligible_workers if w.gpu_memory >= job.gpu_memory_request),
            None,
        )
        if candidate is None:
            continue

        eligible_workers.remove(candidate)
        worker = await assign_job_to_worker(db, job, candidate)
        if worker is None:
            # Claimed elsewhere between our SELECT and the assignment
            # attempt — leave this job QUEUED for the next cycle.
            continue

        newly_assigned.append(job)

    return newly_assigned
