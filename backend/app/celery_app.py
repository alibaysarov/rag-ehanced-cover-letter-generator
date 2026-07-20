import os

from celery import Celery
from kombu import Queue

celery_app = Celery(
    "app",
    broker=os.getenv("CELERY_BROKER_URL"),
    include=["app.tasks"]
)
celery_app.conf.task_default_queue = "default"

celery_app.conf.task_queues = (
    Queue("default"),
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    timezone="UTC",

    task_routes={
        "app.tasks.single_generation": {
            "queue": "default",
        }
    }
)