import os
from celery import Celery


def get_worker_pool():
    return os.getenv("CELERY_WORKER_POOL", "prefork")


def get_concurrency():
    return int(os.getenv("CELERY_WORKER_CONCURRENCY", "1"))


celery_app = Celery(
    "pipelinex",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # execution model
    worker_pool=get_worker_pool(),
    worker_concurrency=get_concurrency(),

    # important for long-running jobs
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# auto-discover tasks
import tasks.job_execution

