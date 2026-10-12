from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "nimbus",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks.scheduling"],
)
celery_app.conf.update(
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "schedule-pending-jobs": {
            "task": "nimbus.scheduler.run",
            "schedule": settings.SCHEDULER_POLL_INTERVAL_SECONDS,
        }
    },
    task_routes={"nimbus.scheduler.*": {"queue": "nimbus.scheduling"}},
)
