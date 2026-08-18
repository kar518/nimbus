"""
Celery task: scheduler.
"""

import asyncio
import threading

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.services.scheduler_service import run_scheduling_cycle
from app.workers.celery_app import celery_app
from app.workers.tasks.execution import execute_job

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


async def _run_scheduling_cycle() -> int:
    async with AsyncSessionLocal() as db:
        assigned_jobs = await run_scheduling_cycle(db)

    for job in assigned_jobs:
        execute_job.delay(str(job.id))

    return len(assigned_jobs)


@celery_app.task(name="nimbus.scheduler.run")
def run() -> int:
    assigned = _get_loop_runner().run(_run_scheduling_cycle())

    if assigned:
        logger.info("scheduler.cycle_complete", assigned=assigned)

    return assigned
