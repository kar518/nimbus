"""
Celery task: job execution.
"""

import asyncio
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.job import Job, JobStatus
from app.models.worker import GPUWorker, WorkerStatus
from app.services.event_bus import publish_event
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


class _EventLoopRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="nimbus-async-loop",
        )
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.close()


_loop_runner: _EventLoopRunner | None = None


def _get_loop_runner() -> _EventLoopRunner:
    global _loop_runner
    if _loop_runner is None:
        _loop_runner = _EventLoopRunner()
    return _loop_runner


async def _release_worker(
    db: AsyncSession,
    worker: GPUWorker | None,
) -> None:
    """Free the worker so the scheduler can assign it a new job."""
    if worker is None:
        return

    worker.current_job = None

    if worker.status != WorkerStatus.OFFLINE:
        worker.status = WorkerStatus.IDLE

    await db.commit()
    await db.refresh(worker)

    await publish_event(
        "worker.status",
        {
            "id": str(worker.id),
            "status": worker.status.value,
            "current_job": None,
        },
    )


async def _run_job(job_id: str) -> str:
    async with AsyncSessionLocal() as db:
        job_result = await db.execute(
            select(Job).where(Job.id == uuid.UUID(job_id))
        )
        job = job_result.scalar_one_or_none()

        if job is None:
            logger.warning("execution.job_not_found", job_id=job_id)
            return JobStatus.FAILED.value

        worker: GPUWorker | None = None

        if job.worker_id is not None:
            worker_result = await db.execute(
                select(GPUWorker).where(GPUWorker.id == job.worker_id)
            )
            worker = worker_result.scalar_one_or_none()

        try:
            await asyncio.sleep(0)
            job.status = JobStatus.COMPLETED

        except Exception:
            logger.exception("execution.job_failed", job_id=job_id)
            job.status = JobStatus.FAILED

        finally:
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await db.commit()
            await db.refresh(job)

        await publish_event(
            "job.status",
            {
                "id": str(job.id),
                "status": job.status.value,
                "worker_id": str(job.worker_id) if job.worker_id else None,
            },
        )

        await _release_worker(db, worker)

        return job.status.value


@celery_app.task(
    name="nimbus.jobs.execute",
    bind=True,
    max_retries=3,
)
def execute_job(self, job_id: str) -> str:
    try:
        return _get_loop_runner().run(_run_job(job_id))

    except Exception as exc:
        logger.exception("execution.task_error", job_id=job_id)
        raise self.retry(exc=exc, countdown=5) from exc
