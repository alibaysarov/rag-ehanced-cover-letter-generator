import asyncio
import json
import logging

from app.cache.redis import async_client
from app.celery_app import celery_app
from app.commands import (
    GenerateLetterCommand,
    build_handler,
)
from app.database import async_session_maker
from app.decorators import async_task
from app.services.task_progress import set_cover_letter_task_status

logger = logging.getLogger(__name__)


async def publish_event(batch_id: str, vacancy_id: int, status: str):
    try:
        await async_client.publish(
            "cover_letter_events",
            json.dumps(
                {"batch_id": batch_id, "vacancy_id": vacancy_id, "status": status}
            ),
        )
    except Exception as e:
        logger.error("Erro during publishing event", e)


@celery_app.task(
    bind=True,
    name="app.tasks.test_task",
    queue="default",
)
@async_task
async def test_task(
    self, vacancy_id: int, first_name: str, last_name: str, batch_id: str
):
    await asyncio.sleep(5)
    await publish_event(batch_id, vacancy_id, "generated")


@celery_app.task(
    bind=True,
    name="app.tasks.single_generation",
    queue="default",
)
@async_task
async def single_generation(
    self, vacancy_id: int, first_name: str, last_name: str, batch_id: str
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
            await handler.handle(command=command)
            set_cover_letter_task_status(batch_id, vacancy_id, "generated")
            await publish_event(batch_id, vacancy_id, "generated")
        except Exception as e:
            set_cover_letter_task_status(batch_id, vacancy_id, "failed")
            raise
