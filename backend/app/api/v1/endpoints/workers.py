import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import admin_user, current_user, registration_auth, worker_auth
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.job import Job, JobStatus
from app.models.user import User
from app.models.worker import GPUWorker
from app.schemas.job import ExecutionLease, ExecutionResult, JobResponse, LogAppend
from app.schemas.worker import DrainRequest, Heartbeat, WorkerCreate, WorkerResponse
from app.services import job_service, worker_service
from app.services.event_bus import publish_event

router = APIRouter(tags=["workers"])


@router.post("/register", dependencies=[Depends(registration_auth)], status_code=201)
async def register(data: WorkerCreate, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    worker = await worker_service.create_worker(db, data)
    token = create_access_token(
        str(worker.id), timedelta(days=30), {"kind": "worker", "session": str(worker.session_id)}
    )
    return {"worker": WorkerResponse.model_validate(worker), "token": token}


@router.get("", response_model=list[WorkerResponse])
async def list_workers(
    _: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[GPUWorker]:
    return await worker_service.get_workers(db)


@router.post(
    "/{worker_id}/heartbeat", response_model=WorkerResponse, dependencies=[Depends(worker_auth)]
)
async def heartbeat(
    worker_id: uuid.UUID, data: Heartbeat, db: AsyncSession = Depends(get_db)
) -> GPUWorker:
    return await worker_service.heartbeat_worker(db, worker_id, data.gpu_utilization)


@router.post("/{worker_id}/drain", response_model=WorkerResponse)
async def drain(
    worker_id: uuid.UUID,
    data: DrainRequest,
    _: User = Depends(admin_user),
    db: AsyncSession = Depends(get_db),
) -> GPUWorker:
    await job_service.transition_lock(db)
    worker = await db.get(GPUWorker, worker_id)
    if not worker:
        raise HTTPException(404, "Worker not found.")
    worker.draining = data.draining
    await db.commit()
    await publish_event("worker.status", {"id": str(worker.id)})
    return worker


@router.get("/{worker_id}/assignment", dependencies=[Depends(worker_auth)])
async def assignment(
    worker_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, Any] | None:
    worker = await db.get(GPUWorker, worker_id)
    if not worker:
        raise HTTPException(404, "Worker not found.")
    if not worker.current_job:
        return None
    job = await job_service.get_job_by_id(db, worker.current_job)
    if job.status != JobStatus.ASSIGNED:
        return None
    return {"job": JobResponse.model_validate(job), "execution_token": str(job.execution_token)}


@router.post(
    "/{worker_id}/jobs/{job_id}/claim",
    response_model=JobResponse,
    dependencies=[Depends(worker_auth)],
)
async def claim(
    worker_id: uuid.UUID,
    job_id: uuid.UUID,
    data: ExecutionLease,
    db: AsyncSession = Depends(get_db),
) -> Job:
    await job_service.transition_lock(db)
    job = await job_service.leased_job(db, worker_id, job_id, data.execution_token)
    worker = await db.get(GPUWorker, worker_id)
    if job.status != JobStatus.ASSIGNED or not worker or worker.current_job != job.id:
        raise HTTPException(409, "This assignment has already been claimed or cancelled.")
    job.status = JobStatus.RUNNING
    job.started_at = job_service.now()
    await db.commit()
    await job_service.notify(job)
    return job


@router.post("/{worker_id}/jobs/{job_id}/control", dependencies=[Depends(worker_auth)])
async def control(
    worker_id: uuid.UUID,
    job_id: uuid.UUID,
    data: ExecutionLease,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    job = await job_service.leased_job(db, worker_id, job_id, data.execution_token)
    return {"cancel": job.cancel_requested or job.status != JobStatus.RUNNING}


@router.post("/{worker_id}/jobs/{job_id}/logs", dependencies=[Depends(worker_auth)])
async def append_logs(
    worker_id: uuid.UUID, job_id: uuid.UUID, data: LogAppend, db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    offset = await job_service.append_logs(
        db, worker_id, job_id, data.execution_token, data.offset, data.text
    )
    return {"offset": offset}


@router.post(
    "/{worker_id}/jobs/{job_id}/finish",
    response_model=JobResponse,
    dependencies=[Depends(worker_auth)],
)
async def finish(
    worker_id: uuid.UUID,
    job_id: uuid.UUID,
    data: ExecutionResult,
    db: AsyncSession = Depends(get_db),
) -> Job:
    return await job_service.finish_job(db, worker_id, job_id, data)


@router.post("/{worker_id}/offline", dependencies=[Depends(worker_auth)])
async def offline(worker_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    from app.models.job import TERMINAL_STATUSES
    from app.models.worker import WorkerStatus

    await job_service.transition_lock(db)
    worker = await db.get(GPUWorker, worker_id)
    if not worker:
        raise HTTPException(404, "Worker not found.")
    if worker.current_job:
        job = await job_service.get_job_by_id(db, worker.current_job)
        if job.status not in TERMINAL_STATUSES:
            job.status = JobStatus.CANCELLED if job.cancel_requested else JobStatus.FAILED
            job.failure_reason = "Worker agent stopped before reporting an outcome."
            job.completed_at = job_service.now()
    worker.current_job = None
    worker.status = WorkerStatus.OFFLINE
    await db.commit()
    await publish_event("worker.status", {"id": str(worker.id)})
    return {"status": "offline"}
