from celery import Celery

from .config import settings

celery_app = Celery(
    "finance_platform",
    # RabbitMQ as the task queue: durable delivery and ack semantics matter
    # for the month-end close chain (a dropped step shouldn't be silent).
    # Redis stays as the result backend — cheap to poll for task status and
    # already running for the pub/sub relay/rate limiter.
    broker=settings.RABBITMQ_URL,
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
