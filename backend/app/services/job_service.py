import base64
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.job import TERMINAL_STATUSES, Job, JobStatus
from app.models.user import User
from app.models.worker import GPUWorker, WorkerStatus
from app.schemas.job import ExecutionResult, JobCreate
from app.services.event_bus import publish_event

LOG_LIMIT = 1_000_000


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def transition_lock(db: AsyncSession) -> None:
    # Serialize lifecycle mutations across API and scheduler processes.
    await db.execute(text("SELECT pg_advisory_xact_lock(6472026)"))


async def notify(job: Job) -> None:
    await publish_event("job.status", {"id": str(job.id)})


async def create_job(db: AsyncSession, job_in: JobCreate, user: User) -> Job:
    job = Job(**job_in.model_dump(), owner_id=user.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await notify(job)
    return job


async def get_jobs(db: AsyncSession, user: User, limit: int = 100, offset: int = 0) -> list[Job]:
    query = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    if not user.is_admin:
        query = query.where(Job.owner_id == user.id)
    return list((await db.scalars(query)).all())


async def get_job_by_id(db: AsyncSession, job_id: uuid.UUID, user: User | None = None) -> Job:
    job = await db.get(Job, job_id)
    if not job or (user and not user.is_admin and job.owner_id != user.id):
        raise HTTPException(404, "Job not found.")
    return job


async def release_worker(db: AsyncSession, job: Job) -> None:
    worker = await db.get(GPUWorker, job.worker_id) if job.worker_id else None
    if worker and worker.current_job == job.id:
        worker.current_job = None
        if worker.status != WorkerStatus.OFFLINE:
            worker.status = WorkerStatus.IDLE


async def cancel_job(db: AsyncSession, job_id: uuid.UUID, user: User) -> Job:
    await transition_lock(db)
    job = await get_job_by_id(db, job_id, user)
    if job.status in TERMINAL_STATUSES:
        raise HTTPException(409, "This job has already finished.")
    job.cancel_requested = True
    if job.status != JobStatus.RUNNING:
        job.status = JobStatus.CANCELLED
        job.completed_at = now()
        await release_worker(db, job)
    await db.commit()
    await notify(job)
    return job


async def retry_job(db: AsyncSession, job_id: uuid.UUID, user: User) -> Job:
    await transition_lock(db)
    previous = await get_job_by_id(db, job_id, user)
    if previous.status not in TERMINAL_STATUSES:
        raise HTTPException(409, "Wait for this job to finish before retrying.")
    if not previous.command:
        raise HTTPException(
            409, "This legacy job has no executable command. Submit a new workload."
        )
    data = {key: getattr(previous, key) for key in JobCreate.model_fields}
    job = Job(**data, owner_id=user.id, retry_of=previous.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await notify(job)
    return job


async def leased_job(
    db: AsyncSession, worker_id: uuid.UUID, job_id: uuid.UUID, token: uuid.UUID
) -> Job:
    job = await get_job_by_id(db, job_id)
    worker = await db.get(GPUWorker, worker_id)
    if not worker or job.worker_id != worker_id or job.execution_token != token:
        raise HTTPException(409, "This execution lease is no longer valid.")
    return job


async def append_logs(
    db: AsyncSession,
    worker_id: uuid.UUID,
    job_id: uuid.UUID,
    token: uuid.UUID,
    offset: int,
    chunk: str,
) -> int:
    await transition_lock(db)
    job = await leased_job(db, worker_id, job_id, token)
    if job.status != JobStatus.RUNNING:
        raise HTTPException(409, "This job is no longer running.")
    current = len(job.log_text)
    if offset == current:
        job.log_text += chunk[: max(0, LOG_LIMIT - current)]
        await db.commit()
        await publish_event("job.logs", {"id": str(job.id)})
    elif offset > current:
        raise HTTPException(409, "Log offset is ahead of the stored stream.")
    return len(job.log_text)


async def finish_job(
    db: AsyncSession, worker_id: uuid.UUID, job_id: uuid.UUID, result: ExecutionResult
) -> Job:
    await transition_lock(db)
    job = await leased_job(db, worker_id, job_id, result.execution_token)
    if job.status in TERMINAL_STATUSES:
        return job
    if job.status != JobStatus.RUNNING:
        raise HTTPException(409, "Claim this assignment before reporting its outcome.")
    job.exit_code = result.exit_code
    job.failure_reason = result.reason
    job.status = (
        JobStatus.CANCELLED
        if job.cancel_requested
        else (
            JobStatus.COMPLETED if result.exit_code == 0 and not result.reason else JobStatus.FAILED
        )
    )
    if job.status == JobStatus.FAILED and not job.failure_reason:
        job.failure_reason = f"Container exited with code {result.exit_code}."
    job.completed_at = now()
    total = 0
    for upload in result.artifacts:
        content = base64.b64decode(upload.content_base64)
        total += len(content)
        if total > 8 * 1024 * 1024:
            raise HTTPException(422, "Combined artifacts may be at most 8 MB.")
        db.add(
            Artifact(job_id=job.id, filename=upload.filename, size=len(content), content=content)
        )
    await release_worker(db, job)
    await db.commit()
    await notify(job)
    return job
