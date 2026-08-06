"""
Celery application instance.

Task modules are auto-discovered from `app.workers.tasks.*` (see the
`include` list below). No tasks are implemented yet — this wires up the
app, queues, and serialization so tasks can be added without touching
this file.

Run a worker locally with:
    celery -A app.workers.celery_app worker --loglevel=info

Run the beat scheduler (for periodic tasks, once defined) with:
    celery -A app.workers.celery_app beat --loglevel=info
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "nimbus",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        # "app.workers.tasks.scheduling",
        # "app.workers.tasks.workload_execution",
    ],
)

celery_app.conf.update(
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    task_routes={
        # Future example:
        # "app.workers.tasks.scheduling.*": {"queue": "nimbus.scheduling"},
    },
)
