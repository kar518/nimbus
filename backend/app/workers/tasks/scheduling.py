import asyncio

from app.db.session import AsyncSessionLocal
from app.services.scheduler_service import run_scheduling_cycle
from app.workers.celery_app import celery_app


async def _cycle() -> int:
    async with AsyncSessionLocal() as db:
        return len(await run_scheduling_cycle(db))


# Celery's decorator is untyped in the installed library.
@celery_app.task(name="nimbus.scheduler.run")  # type: ignore[misc]
def run() -> int:
    return asyncio.run(_cycle())
