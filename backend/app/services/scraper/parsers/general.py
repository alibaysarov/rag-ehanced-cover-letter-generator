import asyncio
import logging
import os
from abc import abstractmethod
from urllib.parse import urlencode

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.decorators.browser import simple_page
from app.helper.flatten_list import flatten_list
from app.job_parser.hh_parser import Vacancy
from app.schemas.vacancy.single_vacancy import SingleVacancy


def async_retry():
    """Декоратор с exponential backoff: 3 попытки, задержки 1s → 2s → 4s."""
    return retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(PlaywrightTimeoutError|Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

logger = logging.getLogger(__name__)

HH_MAX_PAGES = int(os.getenv("HH_MAX_PAGES", "5"))


class GeneralVacancyParser:
    
    def __init__(self,name:str,base_url:str,has_pagination:bool):
        self._name = name
        self._base_url = base_url
        self._has_pagination:str = has_pagination
    
    def get_name(self)->str:
        return self._name
    
    @abstractmethod
    def get_single_url(self,vacancy_id)->str:
        """Write JS function that returns list of objects:
            {title, vacancy_id, link}
        """
        ...
    
    
    @abstractmethod
    def evaluate_pagination(self)->str:
        """
        Write JS function that returns list of pagination numbers:
            {title, vacancy_id, link}
            Example:
            () => Array.from(document.querySelectorAll('[data-qa^=pager-page]'))
                    .map(v =>v.textContent || null).filter((item) =>item != null)
        """
        ...
    @abstractmethod        
    def evaluate_vacancy_list(self)->str:
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
    
    def evaluate_vacancy_page(self)->str:
        """
        Write JS function that returns vacancy object:
            {title, vacancy_id, link}
            Example:
            () => {job_title,job_text}
        """
        
        ...
        
        
    async def get_list(self,browser,text:str,job_id: int)->list[Vacancy]:
        async with simple_page(browser,self._base_url) as page:
            try:
                if self._has_pagination:
                    return await self._get_paginated_list(page=page,text=text,job_id=job_id)
                else:
                    return await self._get_vacancies_by_scroll(page=page,text=text)
            except Exception as e:
                logger.warning(f"Error getting list: {e}")    
    
    async def parse_single_vacancy(self,page:Page,vacancy_id)->SingleVacancy:
        
        url = self.get_single_url(vacancy_id)
        try:
            await page.route("**/*", self._block_resources)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            vacancy = await self._get_result_from_vacancy(page=page)
            return vacancy
        except Exception as e:
            logger.warning(f"Error getting single vacancy page {vacancy_id} : {e}")
    
    async def _get_vacancies_by_scroll(self,page,text:str)->list[Vacancy]:
        try:
            url = self.format_url(self._base_url,text=text)
            await page.route("**/*", self._block_resources)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return await self._get_results_from_page(page)
        except Exception as e:
            logger.error(f"Error getting list: {e}")
        
    @async_retry()
    async def _get_vacancies_by_page(self,page,query:str,page_num:int)->list[Vacancy]:
        try:
            await page.route("**/*", self._block_resources)
            url = self.format_url(self._base_url,text=query,page=page_num)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            return await self._get_results_from_page(page)
        except Exception as e:
            logger.error(f"Error getting list: {e}")
            raise

    @async_retry()
    async def _get_result_from_vacancy(self, page:Page)->SingleVacancy:
        try:
            await self._scroll_page(page)
            await page.wait_for_timeout(500)
            vacancy_dict = await page.evaluate(self.evaluate_vacancy_page())
            vacancy:SingleVacancy = SingleVacancy.model_validate(vacancy_dict)
            return vacancy
        except Exception as e:
            logger.error("Error during parsing single vacancy page")
            raise e
        
    async def _get_results_from_page(self, page)->list[Vacancy]:
        await self._scroll_page(page)
        await page.wait_for_timeout(500)
            
        cards = await page.evaluate(self.evaluate_vacancy_list())
            
        result = [
                Vacancy(name=card['title'],link=card['link'],vacancy_id=card['vacancy_id'])
                for card in cards
            ]
        return result
    
    
    def format_url(self,url: str, **kwargs) -> str:
        return f"{url}?{urlencode(kwargs)}"
    
    @async_retry()
    async def _get_total_pages(self,page,text:str)->int:
        url =self.format_url(self._base_url,text=text)
        try:
            await page.route("**/*", self._block_resources)
            
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
    
    async def _block_resources(self,route, request):
        if request.resource_type in ("image", "font", "media", "stylesheet"):
            await route.abort()
        else:
            await route.continue_()
    
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
    
    

    async def _scroll_page(self,page):
        await page.evaluate("""
            () => new Promise((resolve) => {
                const distance = 300;       // пикселей за шаг
                const delay = 100;          // мс между шагами
                
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    
                    const scrolled = window.scrollY + window.innerHeight;
                    const total = document.documentElement.scrollHeight;
                    
                    if (scrolled >= total) {
                        clearInterval(timer);
                        resolve();
                    }
                }, delay);
            })
        """)