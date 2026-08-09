"""
Job service layer.

Endpoints delegate persistence here rather than talking to the session
directly, so scheduling/business logic added later has a single place to
live alongside (not inside) the API layer.
"""

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
