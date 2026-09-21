import asyncio
import logging
from abc import abstractmethod

from playwright.async_api import Page
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
)

from app.decorators.browser import simple_page
from app.helper import get_domain_by_url, scroll_page_bottom, secure_request_route
from app.helper.flatten_list import flatten_list
from app.schemas.vacancy.single_vacancy import SingleVacancy
from app.schemas.vacancy.vacancy import Vacancy


def async_retry():
    """Three retries after 10, 15, and 20 seconds for slow vacancy pages."""
    return retry(
        stop=stop_after_attempt(4),
        wait=wait_chain(wait_fixed(10), wait_fixed(15), wait_fixed(20)),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


logger = logging.getLogger(__name__)

PAGE_GOTO_TIMEOUT_MS = 30_000
JS_TIMEOUT_SECONDS = 10
MAX_RESULT_CARDS = 2000


class GeneralVacancyParser:
    def __init__(
        self,
        name: str,
        base_url: str,
        has_pagination: bool,
        *,
        site_key: str | None = None,
        pagination_start: int = 0,
        max_pages: int = 5,
    ):
        self._name = name
        self._site_key = site_key or get_domain_by_url(base_url)
        self._base_url = base_url
        self._has_pagination = has_pagination
        self._pagination_start = pagination_start
        self._max_pages = max_pages

    def get_name(self) -> str:
        return self._name

    def get_site_key(self) -> str:
        return self._site_key

    @abstractmethod
    def get_single_url(self, vacancy_id) -> str:
        """Write JS function that returns list of objects:
        {title, vacancy_id, link}
        """
        ...

    @abstractmethod
    def evaluate_pagination(self) -> str:
        """
        Write JS function that returns list of pagination numbers:
            {title, vacancy_id, link}
            Example:
            () => Array.from(document.querySelectorAll('[data-qa^=pager-page]'))
                    .map(v =>v.textContent || null).filter((item) =>item != null)
        """
        ...

    @abstractmethod
    def evaluate_vacancy_list(self) -> str:
        """
        Write JS function that returns list of objects:
            {title, vacancy_id, link}
            Example:
            () => Array.from(document.querySelectorAll('[data-qa^=vacancy-serp__vacancy]'))
                    .map(v => {
                        const title = v.querySelector('[data-qa=serp-item__title-text]')?.textContent || null;

                        const link = v.querySelector('a')?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/(\d+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
        """
        ...

    def evaluate_vacancy_page(self) -> str:
        """
        Write JS function that returns vacancy object:
            {title, vacancy_id, link}
            Example:
            () => {job_title,job_text}
        """

        ...

    async def get_list(self, browser, text: str, job_id: int) -> list[Vacancy]:
        async with simple_page(browser, self._base_url) as page:
            try:
                if self._has_pagination:
                    return await self._get_paginated_list(
                        page=page, text=text, job_id=job_id
                    )
                else:
                    return await self._get_vacancies_by_scroll(page=page, text=text)
            except Exception as e:
                logger.warning(f"Error getting list: {e}", exc_info=True)
                raise

    @async_retry()
    async def parse_single_by_url(self, page: Page, url: str) -> SingleVacancy:
        try:
            await page.route("**/*", secure_request_route)
            await page.goto(
                url, wait_until="domcontentloaded", timeout=PAGE_GOTO_TIMEOUT_MS
            )
            vacancy = await self._get_result_from_vacancy(page=page)
            vacancy.job_url = page.url
            return vacancy
        except Exception as e:
            logger.warning(
                f"Error getting single vacancy page url:{url} : {e}", exc_info=True
            )
            raise

    async def parse_single_vacancy(self, page: Page, vacancy_id) -> SingleVacancy:

        url = self.get_single_url(vacancy_id)
        try:
            vacancy = await self.parse_single_by_url(page=page, url=url)
            return vacancy
        except Exception as e:
            logger.warning(
                f"Error getting single vacancy page {vacancy_id} : {e}", exc_info=True
            )
            raise

    async def _get_vacancies_by_scroll(self, page, text: str) -> list[Vacancy]:
        try:
            url = self.format_url(self._base_url, text=text)
            await page.route("**/*", secure_request_route)
            await page.goto(
                url, wait_until="domcontentloaded", timeout=PAGE_GOTO_TIMEOUT_MS
            )
            return await self._get_results_from_page(page)
        except Exception as e:
            logger.error(f"Error getting list: {e}", exc_info=True)
            raise

    @async_retry()
    async def _get_vacancies_by_page(
        self, page, query: str, page_num: int
    ) -> list[Vacancy]:
        try:
            await page.route("**/*", secure_request_route)
            url = self.format_url(self._base_url, text=query, page=page_num)
            await page.goto(
                url, wait_until="domcontentloaded", timeout=PAGE_GOTO_TIMEOUT_MS
            )

            return await self._get_results_from_page(page)
        except Exception as e:
            logger.error(f"Error getting list: {e}")
            raise

    async def _get_result_from_vacancy(self, page: Page) -> SingleVacancy:
        try:
            await scroll_page_bottom(page)
            await page.wait_for_timeout(500)
            vacancy_dict = await asyncio.wait_for(
                page.evaluate(self.evaluate_vacancy_page()), timeout=JS_TIMEOUT_SECONDS
            )
            if not isinstance(vacancy_dict, dict):
                raise ValueError(
                    f"{self._name}: evaluate_vacancy_page must return an object"
                )
            vacancy: SingleVacancy = SingleVacancy.model_validate(vacancy_dict)
            if not vacancy.job_text.strip():
                raise ValueError(
                    f"{self._name}: evaluate_vacancy_page returned empty job_text"
                )
            return vacancy
        except Exception as e:
            logger.error("Error during parsing single vacancy page")
            raise e

    async def _get_results_from_page(self, page) -> list[Vacancy]:
        await scroll_page_bottom(page)
        await page.wait_for_timeout(500)

        cards = await asyncio.wait_for(
            page.evaluate(self.evaluate_vacancy_list()), timeout=JS_TIMEOUT_SECONDS
        )
        if not isinstance(cards, list):
            raise ValueError(
                f"{self._name}: evaluate_vacancy_list must return an array"
            )
        if len(cards) > MAX_RESULT_CARDS:
            raise ValueError(
                f"{self._name}: evaluate_vacancy_list returned too many cards"
            )

        result = []
        for card in cards:
            if not isinstance(card, dict):
                raise ValueError(f"{self._name}: vacancy list item must be an object")
            try:
                vacancy = Vacancy(
                    name=str(card["title"]).strip(),
                    link=str(card["link"]).strip(),
                    vacancy_id=str(card["vacancy_id"]).strip(),
                )
            except (KeyError, TypeError) as exc:
                raise ValueError(f"{self._name}: invalid vacancy list item") from exc
            if (
                not vacancy.name
                or not vacancy.vacancy_id
                or not vacancy.link.startswith(("http://", "https://"))
            ):
                raise ValueError(f"{self._name}: invalid vacancy list item values")
            result.append(vacancy)
        return result

    def format_url(self, url: str, **kwargs) -> str:
        raise NotImplementedError

    @async_retry()
    async def _get_total_pages(self, page, text: str) -> int:
        url = self.format_url(self._base_url, text=text)
        try:
            await page.route("**/*", secure_request_route)

            await page.goto(
                url, wait_until="domcontentloaded", timeout=PAGE_GOTO_TIMEOUT_MS
            )

            # pages = await page.query_selector_all(self._pagination_elems)

            pages_texts = await asyncio.wait_for(
                page.evaluate(self.evaluate_pagination()), timeout=JS_TIMEOUT_SECONDS
            )
            logger.info(f"paged texts {pages_texts}")
            if not isinstance(pages_texts, list):
                raise ValueError(
                    f"{self._name}: evaluate_pagination must return an array"
                )
            if not pages_texts:
                return 1
            valid_pages: list[int] = []
            for value in pages_texts:
                if isinstance(value, bool):
                    continue
                text_value = str(value).strip()
                if text_value.isdigit() and int(text_value) > 0:
                    valid_pages.append(int(text_value))
            return min(max(valid_pages), self._max_pages) if valid_pages else 1

        except Exception as e:
            logger.error(f"Error getting total pages: {e}")
            raise

    async def _get_paginated_list(self, page, text: str, job_id: int) -> list[Vacancy]:
        pages = await self._get_total_pages(page, text=text)
        logger.info(f"[job={job_id}] Total pages to scrape: {pages}")

        browser = page.context.browser

        async def fetch_page(page_num: int) -> list[Vacancy]:
            new_page = await browser.new_page()
            try:
                return await self._get_vacancies_by_page(new_page, text, page_num)
            finally:
                await new_page.close()

        tasks = [fetch_page(self._pagination_start + i) for i in range(pages)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            raise failures[0]
        return flatten_list(results)
