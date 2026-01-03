import os
import platform
from celery import Celery


def get_worker_pool():
    return os.getenv(
        "CELERY_WORKER_POOL",
        "solo" if platform.system() == "Windows" else "prefork",
    )


def get_concurrency():
    if platform.system() == "Windows":
        return 1
    return int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))


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
    worker_pool=get_worker_pool(),
    worker_concurrency=get_concurrency(),
)

# auto-discover tasks
import tasks.job_execution

