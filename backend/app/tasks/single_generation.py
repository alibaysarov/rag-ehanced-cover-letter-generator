import asyncio
import logging

from app.celery_app import celery_app
from app.commands import (
    GenerateLetterCommand,
    build_handler,
)
from app.database import async_session_maker
from app.decorators import async_task
from app.pubsub.publish_event import publish_event_sync
from app.services.task_progress import set_cover_letter_task_status

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.test_task",
    queue="default",
)
@async_task
async def test_task(
    self, user_id: int, vacancy_id: int, first_name: str, last_name: str, batch_id: str
):
    cover_letter_text = f"test123 {first_name} {last_name}"
    data = {
        "user_id": user_id,
        "batch_id": batch_id,
        "vacancy_id": vacancy_id,
        "status": "generated",
        "cover_letter_text": cover_letter_text,
    }

    await asyncio.sleep(2)
    publish_event_sync("cover_letter_events", data)


@celery_app.task(
    bind=True,
    name="app.tasks.single_generation",
    queue="default",
)
@async_task
async def single_generation(
    self, user_id: int, vacancy_id: int, first_name: str, last_name: str, batch_id: str
):
    async with async_session_maker() as session:
        command = GenerateLetterCommand(
            vacancy_id=vacancy_id,
            first_name=first_name,
            last_name=last_name,
            batch_id=batch_id,
        )
        handler = build_handler(session=session)
        try:
            set_cover_letter_task_status(batch_id, vacancy_id, "started")
            cover_letter_text = await handler.handle(command=command)
            set_cover_letter_task_status(batch_id, vacancy_id, "generated")
            data = {
                "user_id": user_id,
                "batch_id": batch_id,
                "vacancy_id": vacancy_id,
                "status": "generated",
                "cover_letter_text": cover_letter_text,
            }
            publish_event_sync("cover_letter_events", data)
        except Exception as e:
            set_cover_letter_task_status(batch_id, vacancy_id, "failed")
            raise
