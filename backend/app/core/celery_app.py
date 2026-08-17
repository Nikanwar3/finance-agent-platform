from celery import Celery

from .config import settings

celery_app = Celery(
    "finance_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Month-end close runs a chain of financial-agent calls per company; give
    # a single task room to run without a worker reaping it as "stuck".
    task_time_limit=15 * 60,
    task_soft_time_limit=10 * 60,
)

celery_app.autodiscover_tasks(["app.workers"])
