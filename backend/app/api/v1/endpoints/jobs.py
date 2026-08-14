"""
Job submission endpoints.

Creation, listing, and single-job lookup are implemented here.
Cancellation, scheduling, and worker assignment are out of scope for
this feature — see the root README's roadmap.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.job import JobCreate, JobResponse
from app.services import job_service

router = APIRouter(tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(job_in: JobCreate, db: AsyncSession = Depends(get_db)) -> JobResponse:
    job = await job_service.create_job(db, job_in)
    return JobResponse.model_validate(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs(db: AsyncSession = Depends(get_db)) -> list[JobResponse]:
    jobs = await job_service.get_jobs(db)
    return [JobResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> JobResponse:
    job = await job_service.get_job_by_id(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(job)
