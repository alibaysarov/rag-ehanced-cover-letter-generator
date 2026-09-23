import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Protocol

from app.models import AutoParsedJob
from app.repository.parsing_job_repository import ParsingJobRepository
from app.schemas.vacancy.vacancy import Vacancy


class VacancyParserRuntime(Protocol):
    async def get_list(self, text: str, job_id: int) -> list[Vacancy]:
        raise NotImplementedError

    async def parse_single_vacancy(self, vacancy_id: str):
        raise NotImplementedError

    async def aclose(self) -> None:
        raise NotImplementedError


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
        runtime: VacancyParserRuntime | None = None,
        parser=None,
        browser=None,
        vacancy_limit: int | None = None,
    ) -> None:
        if runtime is None:
            if parser is None or browser is None:
                raise ValueError("runtime is required")
            runtime = _LegacyCompatibilityRuntime(parser, browser)
        try:
            if vacancy_limit is not None and vacancy_limit < 1:
                raise ValueError("vacancy_limit must be positive")
            vacancy_list = await runtime.get_list(query, job_id)
            vacancies = self._unique_vacancies(vacancy_list)
            if vacancy_limit is not None:
                vacancies = vacancies[:vacancy_limit]
            await self._repository.record_found(job_id, site_key, len(vacancies))
        except Exception as exc:
            await self._repository.finish_site(
                job_id, site_key, failed=True, error=self._error_message(exc)
            )
            raise

        semaphore = asyncio.Semaphore(4)
        try:
            results = await asyncio.gather(
                *[
                    self._process_vacancy(
                        semaphore=semaphore,
                        runtime=runtime,
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
            await runtime.aclose()

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
        runtime: VacancyParserRuntime | None = None,
        context=None,
        parser=None,
        vacancy: Vacancy,
        job_id: int,
        user_id: int,
        site_key: str,
    ) -> None:
        async with semaphore:
            try:
                if runtime is not None:
                    item = await runtime.parse_single_vacancy(vacancy.vacancy_id)
                else:
                    assert context is not None and parser is not None
                    page = await context.new_page()
                    try:
                        item = await parser.parse_single_vacancy(
                            page, vacancy.vacancy_id
                        )
                    finally:
                        await page.close()
                saved, inserted = await self._repository.save_vacancy(
                    job_id=job_id,
                    site_key=site_key,
                    user_id=user_id,
                    vacancy_id=vacancy.vacancy_id,
                    url=item.job_url,
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


class _LegacyCompatibilityRuntime(VacancyParserRuntime):
    """Temporary adapter for callers still using the pre-runtime service API."""

    def __init__(self, parser, browser):
        self.parser = parser
        self.browser = browser
        self.context = None

    async def get_list(self, text: str, job_id: int):
        return await self.parser.get_list(self.browser, text, job_id)

    async def parse_single_vacancy(self, vacancy_id: str):
        if self.context is None:
            self.context = await self.browser.new_context()
        page = await self.context.new_page()
        try:
            return await self.parser.parse_single_vacancy(page, vacancy_id)
        finally:
            await page.close()

    async def aclose(self):
        if self.context is None:
            self.context = await self.browser.new_context()
        if self.context is not None:
            await self.context.close()
