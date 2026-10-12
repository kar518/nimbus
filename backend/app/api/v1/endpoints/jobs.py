import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user
from app.db.session import get_db
from app.models.artifact import Artifact
from app.models.job import TERMINAL_STATUSES, Job, JobStatus
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse
from app.services import job_service
from app.services.scheduler_service import waiting_reason

router = APIRouter(tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=201)
async def submit_job(
    job_in: JobCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Job:
    return await job_service.create_job(db, job_in, user)


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    q: str = Query("", max_length=255),
    status: JobStatus | None = None,
    history: bool = False,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    query = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
    if not user.is_admin:
        query = query.where(Job.owner_id == user.id)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Job.title.ilike("%" + escaped + "%", escape="\\"))
    if status:
        query = query.where(Job.status == status)
    if history:
        query = query.where(Job.status.in_(TERMINAL_STATUSES))
    jobs = list((await db.scalars(query)).all())
    return [
        JobResponse.model_validate(job).model_copy(
            update={"waiting_reason": await waiting_reason(db, job)}
        )
        for job in jobs
    ]


@router.get("/summary")
async def summary(
    user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    ownership = [] if user.is_admin else [Job.owner_id == user.id]
    rows = (
        await db.execute(select(Job.status, func.count()).where(*ownership).group_by(Job.status))
    ).all()
    counts = {status.value: count for status, count in rows}
    cutoff = job_service.now() - timedelta(days=6)
    cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
    daily = (
        await db.execute(
            select(func.date(Job.created_at), func.count())
            .where(*ownership, Job.created_at >= cutoff)
            .group_by(func.date(Job.created_at))
        )
    ).all()
    days = {str(date): count for date, count in daily}
    executions = (
        await db.execute(
            select(Job.status, func.count())
            .where(*ownership, Job.execution_token.is_not(None), Job.status.in_(TERMINAL_STATUSES))
            .group_by(Job.status)
        )
    ).all()
    outcomes = {status.value: count for status, count in executions}
    finished = sum(outcomes.values())
    successful = outcomes.get("COMPLETED", 0)
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "success_rate": round(successful / finished * 100, 1) if finished else None,
        "executions": finished,
        "daily": [
            {
                "date": str((cutoff + timedelta(days=i)).date()),
                "count": days.get(str((cutoff + timedelta(days=i)).date()), 0),
            }
            for i in range(7)
        ],
    }


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> JobResponse:
    job = await job_service.get_job_by_id(db, job_id, user)
    return JobResponse.model_validate(job).model_copy(
        update={"waiting_reason": await waiting_reason(db, job)}
    )


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel(
    job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Job:
    return await job_service.cancel_job(db, job_id, user)


@router.post("/{job_id}/retry", response_model=JobResponse, status_code=201)
async def retry(
    job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Job:
    return await job_service.retry_job(db, job_id, user)


@router.get("/{job_id}/logs")
async def logs(
    job_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    job = await job_service.get_job_by_id(db, job_id, user)
    return {
        "text": job.log_text[offset:],
        "offset": len(job.log_text),
        "truncated": len(job.log_text) >= job_service.LOG_LIMIT,
        "status": job.status,
    }


@router.get("/{job_id}/logs/download")
async def download_logs(
    job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    job = await job_service.get_job_by_id(db, job_id, user)
    return Response(
        job.log_text,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="nimbus-{job.id}.log"'},
    )


@router.get("/{job_id}/artifacts")
async def artifacts(
    job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    await job_service.get_job_by_id(db, job_id, user)
    rows = (await db.scalars(select(Artifact).where(Artifact.job_id == job_id))).all()
    return [{"id": str(row.id), "filename": row.filename, "size": row.size} for row in rows]


@router.get("/{job_id}/artifacts/{artifact_id}")
async def download_artifact(
    job_id: uuid.UUID,
    artifact_id: uuid.UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await job_service.get_job_by_id(db, job_id, user)
    artifact = await db.get(Artifact, artifact_id)
    if not artifact or artifact.job_id != job_id:
        raise HTTPException(404, "Output file not found.")
    return Response(
        artifact.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
