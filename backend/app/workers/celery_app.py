from celery import Celery
from celery.signals import worker_process_init
from celery.schedules import schedule
from app.core.config import settings
celery_app=Celery("nimbus", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND, include=["app.workers.tasks.scheduling","app.workers.tasks.execution"])
celery_app.conf.update(task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE, task_serializer="json", result_serializer="json", accept_content=["json"], timezone="UTC", enable_utc=True, task_track_started=True, task_acks_late=True, worker_prefetch_multiplier=1, result_expires=3600, broker_connection_retry_on_startup=True, beat_schedule={"schedule-pending-jobs":{"task":"nimbus.scheduler.run","schedule":schedule(settings.SCHEDULER_POLL_INTERVAL_SECONDS)}}, task_routes={"nimbus.scheduler.*":{"queue":"nimbus.scheduling"},"nimbus.jobs.*":{"queue":settings.CELERY_TASK_DEFAULT_QUEUE}})


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Dispose inherited SQLAlchemy connections after Celery forks."""
    from app.db.session import engine
    engine.sync_engine.dispose()
