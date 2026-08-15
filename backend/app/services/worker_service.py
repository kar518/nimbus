from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.worker import GPUWorker
from app.schemas.worker import WorkerCreate


async def create_worker(
    db: AsyncSession,
    worker_in: WorkerCreate,
) -> GPUWorker:
    worker = GPUWorker(
        name=worker_in.name,
        gpu_memory=worker_in.gpu_memory,
        gpu_utilization=worker_in.gpu_utilization,
    )

    db.add(worker)
    await db.commit()
    await db.refresh(worker)

    return worker


async def get_workers(db: AsyncSession) -> list[GPUWorker]:
    result = await db.execute(
        select(GPUWorker).order_by(GPUWorker.created_at.desc())
    )
    return list(result.scalars().all())