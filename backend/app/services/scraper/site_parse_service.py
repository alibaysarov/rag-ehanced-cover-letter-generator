import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable

from playwright.async_api import Browser, BrowserContext

from app.models import AutoParsedJob
from app.repository.parsing_job_repository import ParsingJobRepository
from app.schemas.vacancy.vacancy import Vacancy
from app.services.scraper.parsers.general import GeneralVacancyParser

logger = logging.getLogger(__name__)


class SiteParseService:
    """Parse one site and persist every completed detail immediately."""

    def __init__(
        self,
        repository: ParsingJobRepository,
        publish_saved: Callable[[AutoParsedJob], Awaitable[None] | None] | None = None,
    ):
        self._repository = repository
        self._publish_saved = publish_saved

    async def run(
        self,
        *,
        job_id: int,
        user_id: int,
        site_key: str,
        query: str,
        parser: GeneralVacancyParser,
        browser: Browser,
        vacancy_limit: int | None = None,
    ) -> None:
        try:
            if vacancy_limit is not None and vacancy_limit < 1:
                raise ValueError("vacancy_limit must be positive")
            vacancy_list = await parser.get_list(browser, query, job_id)
            vacancies = self._unique_vacancies(vacancy_list)
            if vacancy_limit is not None:
                vacancies = vacancies[:vacancy_limit]
            await self._repository.record_found(job_id, site_key, len(vacancies))
        except Exception as exc:
            await self._repository.finish_site(
                job_id, site_key, failed=True, error=self._error_message(exc)
            )
            raise

        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        semaphore = asyncio.Semaphore(4)
        try:
            results = await asyncio.gather(
                *[
                    self._process_vacancy(
                        semaphore=semaphore,
                        context=context,
                        parser=parser,
                        vacancy=vacancy,
                        job_id=job_id,
                        user_id=user_id,
                        site_key=site_key,
                    )
                    for vacancy in vacancies
                ],
                return_exceptions=True,
            )
        finally:
            await context.close()

        failures = [result for result in results if isinstance(result, Exception)]
        await self._repository.finish_site(
            job_id,
            site_key,
            failed=bool(failures),
            error=(f"{len(failures)} vacancy detail(s) failed" if failures else None),
        )

    async def _process_vacancy(
        self,
        *,
        semaphore: asyncio.Semaphore,
        context: BrowserContext,
        parser: GeneralVacancyParser,
        vacancy: Vacancy,
        job_id: int,
        user_id: int,
        site_key: str,
    ) -> None:
        async with semaphore:
            page = await context.new_page()
            try:
                item = await parser.parse_single_vacancy(page, vacancy.vacancy_id)
                saved, inserted = await self._repository.save_vacancy(
                    job_id=job_id,
                    site_key=site_key,
                    user_id=user_id,
                    vacancy_id=vacancy.vacancy_id,
                    url=item.job_url or parser.get_single_url(vacancy.vacancy_id),
                    job_title=self._normalize_text(item.job_title),
                    job_text=self._normalize_text(item.job_text),
                    company_name=(
                        self._normalize_text(item.company_name)
                        if item.company_name
                        else None
                    ),
                )
                if inserted and saved is not None and self._publish_saved is not None:
                    try:
                        callback_result = self._publish_saved(saved)
                        if inspect.isawaitable(callback_result):
                            await callback_result
                    except Exception:
                        logger.exception("Could not process saved vacancy callback")
            except Exception:
                await self._repository.record_vacancy_failure(job_id, site_key)
                raise
            finally:
                await page.close()

    @staticmethod
    def _unique_vacancies(vacancies: list[Vacancy]) -> list[Vacancy]:
        seen: set[str] = set()
        return [
            vacancy
            for vacancy in vacancies
            if vacancy.vacancy_id
            and not (vacancy.vacancy_id in seen or seen.add(vacancy.vacancy_id))
        ]

    @staticmethod
    def _error_message(exc: Exception) -> str:
        return str(exc)[:500] or exc.__class__.__name__

    @staticmethod
    def _normalize_text(value: str) -> str:
        """Store compact text: whitespace has no semantic value for the LLM prompt."""
        return re.sub(r"\s+", " ", value).strip()
