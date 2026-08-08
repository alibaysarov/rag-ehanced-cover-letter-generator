import os

from celery import Celery
from kombu import Queue


# @worker_process_init.connect
# def init_worker(**kwargs):
#     # закрываем унаследованные из родителя соединения,
#     # чтобы каждый дочерний процесс создал свои собственные при первом использовании
#     engine.sync_engine.dispose(close=False)


celery_app = Celery("app", broker=os.getenv("CELERY_BROKER_URL"), include=["app.tasks"])

celery_app.conf.task_default_queue = "default"

celery_app.conf.task_queues = (Queue("default"),)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_routes={
        "app.tasks.single_generation": {
            "queue": "default",
        },
        "app.tasks.test_task": {
            "queue": "default",
        },
    },
)
