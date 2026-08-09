"""
Job submission endpoints.

Only creation is implemented here. Listing, cancellation, scheduling, and
worker assignment are out of scope for this feature — see the root
README's roadmap.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.job import JobCreate, JobResponse
from app.services import job_service

router = APIRouter(tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(job_in: JobCreate, db: AsyncSession = Depends(get_db)) -> JobResponse:
    job = await job_service.create_job(db, job_in)
    return JobResponse.model_validate(job)
