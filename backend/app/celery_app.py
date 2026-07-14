from celery import Celery
import os


celery_app = Celery(
    "app",
    broker=os.getenv("CELERY_BROKER_URL"),
    backend=os.getenv("CELERY_RESULT_BACKEND"),
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    timezone="UTC",

    task_routes={
        "app.tasks.*": {
            "queue": "default"
        }
    }
)