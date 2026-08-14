"""
Job service layer.

Endpoints delegate persistence here rather than talking to the session
directly, so scheduling/business logic added later has a single place to
live alongside (not inside) the API layer.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobCreate


async def create_job(db: AsyncSession, job_in: JobCreate) -> Job:
    """Persist a new job in the QUEUED state and return it."""
    job = Job(**job_in.model_dump())

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return job


async def get_jobs(db: AsyncSession) -> list[Job]:
    """Return all jobs, most recently created first."""
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
    return list(result.scalars().all())


async def get_job_by_id(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    """Return a single job by id, or None if it doesn't exist."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()
