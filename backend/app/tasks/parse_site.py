import asyncio
import logging

from app.celery_app import celery_app
from app.database import celery_async_session_maker
from app.decorators import async_task
from app.decorators.browser import pw_browser
from app.models import AutoParsedJob
from app.pubsub.publish_event import publish_event_sync
from app.repository.parsing_job_repository import ParsingJobRepository
from app.schemas.api.auto_parse import AutoParsedJobRead, ParsingVacancySavedEvent
from app.services.auto_generate import maybe_start_template_generation_for_vacancy
from app.services.scraper.parsers.registry import create_parser
from app.services.scraper.site_parse_service import SiteParseService

logger = logging.getLogger(__name__)
SITE_PARSE_DEADLINE_SECONDS = 15 * 60


def publish_vacancy_saved(record: AutoParsedJob) -> None:
    if record.id is None or record.parsing_job_id is None:
        raise ValueError("Saved parsing vacancy is missing public identifiers")
    event = ParsingVacancySavedEvent(
        user_id=record.user_id,
        parsing_job_id=record.parsing_job_id,
        site_key=record.web_site or "",
        vacancy=AutoParsedJobRead.model_validate(record),
    )
    publish_event_sync("parsing_events", event.model_dump(mode="json"))


@celery_app.task(name="app.tasks.parse_site", queue="default")
@async_task
async def parse_site(parsing_site_job_id: int) -> None:
    repository = ParsingJobRepository(celery_async_session_maker)
    claimed = await repository.claim_site_by_id(parsing_site_job_id)
    if claimed is None:
        return
    job_id = claimed.parsing_job_id
    site_key = claimed.site_key
    job = await repository.get_job(job_id)
    if job is None:
        return

    async def process_saved_vacancy(record: AutoParsedJob) -> None:
        publish_vacancy_saved(record)
        await maybe_start_template_generation_for_vacancy(
            record, job.generation_mode, repository
        )

    try:
        if claimed.parser_snapshot is None:
            raise ValueError("Parser snapshot is missing")
        parser = create_parser(claimed.parser_snapshot)
        async with pw_browser(headless=True) as browser:
            service = SiteParseService(repository, process_saved_vacancy)
            await asyncio.wait_for(
                service.run(
                    job_id=job_id,
                    user_id=job.user_id,
                    site_key=site_key,
                    query=job.query,
                    parser=parser,
                    browser=browser,
                    vacancy_limit=claimed.vacancy_limit,
                ),
                timeout=SITE_PARSE_DEADLINE_SECONDS,
            )
    except Exception:
        logger.exception("Site parse failed for job=%s site=%s", job_id, site_key)
        await repository.finish_site(
            job_id, site_key, failed=True, error="site parsing failed"
        )
        raise
