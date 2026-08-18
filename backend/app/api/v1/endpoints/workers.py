import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.worker import WorkerCreate, WorkerResponse
from app.services import worker_service

router = APIRouter(tags=["workers"])

@router.post("", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
async def create_worker(worker_in: WorkerCreate, db: AsyncSession = Depends(get_db)) -> WorkerResponse:
    return WorkerResponse.model_validate(await worker_service.create_worker(db, worker_in))

@router.get("", response_model=list[WorkerResponse])
async def list_workers(db: AsyncSession = Depends(get_db)) -> list[WorkerResponse]:
    workers = await worker_service.get_workers(db)
    return [WorkerResponse.model_validate(worker) for worker in workers]

@router.post("/{worker_id}/heartbeat", response_model=WorkerResponse)
async def heartbeat_worker(worker_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> WorkerResponse:
    worker = await worker_service.heartbeat_worker(db, worker_id)
    if worker is None: raise HTTPException(status_code=404, detail="Worker not found")
    return WorkerResponse.model_validate(worker)
