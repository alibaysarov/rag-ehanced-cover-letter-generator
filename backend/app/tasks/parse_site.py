import logging

from app.celery_app import celery_app
from app.database import celery_async_session_maker
from app.decorators import async_task
from app.decorators.browser import pw_browser
from app.models import AutoParsedJob
from app.pubsub.publish_event import publish_event_sync
from app.repository.parsing_job_repository import ParsingJobRepository
from app.schemas.api.auto_parse import AutoParsedJobRead, ParsingVacancySavedEvent
from app.services.scraper.parsers.registry import create_parser
from app.services.scraper.site_parse_service import SiteParseService

logger = logging.getLogger(__name__)


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
async def parse_site(job_id: int, site_key: str) -> None:
    repository = ParsingJobRepository(celery_async_session_maker)
    claimed = await repository.claim_site(job_id, site_key)
    if claimed is None:
        return
    job = await repository.get_job(job_id)
    if job is None:
        return
    try:
        parser = create_parser(site_key)
        async with pw_browser(headless=True) as browser:
            service = SiteParseService(repository, publish_vacancy_saved)
            await service.run(
                job_id=job_id,
                user_id=job.user_id,
                site_key=site_key,
                query=job.query,
                parser=parser,
                browser=browser,
            )
    except Exception:
        logger.exception("Site parse failed for job=%s site=%s", job_id, site_key)
        raise
