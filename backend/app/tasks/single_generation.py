import asyncio
import logging
from typing import Any

from app.celery_app import celery_app
from app.commands import (
    GenerateLetterCommand,
    build_handler,
)

# from app.database import async_session_maker
from app.database import celery_async_session_maker
from app.decorators import async_task
from app.models import AutoParsedJob
from app.pubsub.publish_event import publish_event_sync
from app.repository.auto_parse_job_repository import AutoParseJobRepository
from app.schemas.api.auto_parse import AutoParsedJobRead, TemplateVacancyReadyEvent
from app.schemas.generation_mode import GenerationMode
from app.services.task_progress import set_cover_letter_task_status

logger = logging.getLogger(__name__)


def build_generated_event(
    *,
    user_id: int,
    batch_id: str | int,
    vacancy_id: int,
    cover_letter_text: str,
    mode: GenerationMode,
    vacancy: AutoParsedJob | None = None,
) -> dict[str, Any]:
    if mode == GenerationMode.TEMPLATE:
        if vacancy is None or vacancy.parsing_job_id is None:
            raise LookupError(f"Vacancy {vacancy_id} does not exist")
        return TemplateVacancyReadyEvent(
            user_id=user_id,
            batch_id=batch_id,
            parsing_job_id=vacancy.parsing_job_id,
            vacancy=AutoParsedJobRead.model_validate(vacancy),
        ).model_dump(mode="json")
    return {
        "user_id": user_id,
        "batch_id": batch_id,
        "vacancy_id": vacancy_id,
        "status": "generated",
        "cover_letter_text": cover_letter_text,
    }


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
    publish_event_sync("test_events", data)


@celery_app.task(
    bind=True,
    name="app.tasks.single_generation",
    queue="default",
)
@async_task
async def single_generation(
    self,
    user_id: int,
    vacancy_id: int,
    first_name: str,
    last_name: str,
    batch_id: str,
    generation_mode: str = "ai",
):
    async with celery_async_session_maker() as session:
        mode = GenerationMode(generation_mode)
        command = GenerateLetterCommand(
            vacancy_id=vacancy_id,
            first_name=first_name,
            last_name=last_name,
            batch_id=batch_id,
            generation_mode=mode,
        )
        handler = build_handler(session=session)
        try:
            set_cover_letter_task_status(batch_id, vacancy_id, "started")
            cover_letter_text = await handler.handle(command=command)
            if not isinstance(cover_letter_text, str) or not cover_letter_text.strip():
                raise ValueError("empty cover letter")
            set_cover_letter_task_status(batch_id, vacancy_id, "generated")
            vacancy = (
                await AutoParseJobRepository(session).get_by_id(vacancy_id)
                if mode == GenerationMode.TEMPLATE
                else None
            )
            data = build_generated_event(
                user_id=user_id,
                batch_id=batch_id,
                vacancy_id=vacancy_id,
                cover_letter_text=cover_letter_text,
                mode=mode,
                vacancy=vacancy,
            )
            publish_event_sync("cover_letter_events", data)
        except Exception as e:
            set_cover_letter_task_status(batch_id, vacancy_id, "failed")
            raise
