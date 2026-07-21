import asyncio
import logging
import os
from abc import abstractmethod
from urllib.parse import urlencode

from playwright.async_api import Page
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.decorators.browser import simple_page
from app.helper import block_resources, get_domain_by_url, scroll_page_bottom
from app.helper.flatten_list import flatten_list
from app.job_parser.hh_parser import Vacancy
from app.schemas.vacancy.single_vacancy import SingleVacancy


def async_retry():
    """Декоратор с exponential backoff: 3 попытки, задержки 1s → 2s → 4s."""
    return retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


logger = logging.getLogger(__name__)

HH_MAX_PAGES = int(os.getenv("HH_MAX_PAGES", "5"))


class GeneralVacancyParser:
    def __init__(self, name: str, base_url: str, has_pagination: bool):

        self._name = get_domain_by_url(base_url)
        print("Parser name", self._name)
        self._base_url = base_url
        self._has_pagination = has_pagination

    def get_name(self) -> str:
        return self._name

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
            await page.route("**/*", block_resources)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            vacancy = await self._get_result_from_vacancy(page=page)
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
            await page.route("**/*", block_resources)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return await self._get_results_from_page(page)
        except Exception as e:
            logger.error(f"Error getting list: {e}", exc_info=True)
            raise

    @async_retry()
    async def _get_vacancies_by_page(
        self, page, query: str, page_num: int
    ) -> list[Vacancy]:
        try:
            await page.route("**/*", block_resources)
            url = self.format_url(self._base_url, text=query, page=page_num)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            return await self._get_results_from_page(page)
        except Exception as e:
            logger.error(f"Error getting list: {e}")
            raise

    async def _get_result_from_vacancy(self, page: Page) -> SingleVacancy:
        try:
            await scroll_page_bottom(page)
            await page.wait_for_timeout(500)
            vacancy_dict = await page.evaluate(self.evaluate_vacancy_page())
            vacancy: SingleVacancy = SingleVacancy.model_validate(vacancy_dict)
            return vacancy
        except Exception as e:
            logger.error("Error during parsing single vacancy page")
            raise e

    async def _get_results_from_page(self, page) -> list[Vacancy]:
        await scroll_page_bottom(page)
        await page.wait_for_timeout(500)

        cards = await page.evaluate(self.evaluate_vacancy_list())

        result = [
            Vacancy(
                name=card["title"], link=card["link"], vacancy_id=card["vacancy_id"]
            )
            for card in cards
        ]
        return result

    def format_url(self, url: str, **kwargs) -> str:
        return f"{url}?{urlencode(kwargs)}"

    @async_retry()
    async def _get_total_pages(self, page, text: str) -> int:
        url = self.format_url(self._base_url, text=text)
        try:
            await page.route("**/*", block_resources)

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # pages = await page.query_selector_all(self._pagination_elems)

            pages_texts = await page.evaluate(self.evaluate_pagination())
            logger.info(f"paged texts {pages_texts}")
            if not pages_texts:
                return 1

            max_page = max(int(t) for t in pages_texts if t.isdigit())
            return min(max_page, HH_MAX_PAGES)

        except Exception as e:
            logger.error(f"Error getting total pages: {e}")
            return 1

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

        tasks = [fetch_page(i) for i in range(pages)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid = [r for r in results if isinstance(r, list)]
        return flatten_list(valid)
