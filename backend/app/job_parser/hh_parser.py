
'''
https://hh.ru/search/vacancy?text=php+%D1%80%D0%B0%D0%B7%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D1%87%D0%B8%D0%BA&area=1&page=0&search_session_id=14c18ffd-9fa9-4ea2-9271-f2dde06ea175
'''

from app.pw_instances.chromium import start_browser,close_browser,get_browser
from app.decorators.time_perf import time_performance
from urllib.parse import quote_plus
from pydantic import BaseModel
from itertools import chain

import asyncio
import os
import logging

logger = logging.getLogger(__name__)
HH_MAX_PAGES = int(os.getenv("HH_MAX_PAGES", "5"))
VACANCIES_URL = "https://hh.ru/search/vacancy?text={query}&page={page}"


def _flatten_list(nested_list)->list:
    return list(chain.from_iterable(nested_list))

class Vacancy(BaseModel):
    name:str
    link:str
    vacancy_id:str

class AutoParserHH:
    
    async def get_vacancies_by_name(self,browser,text:str,job_id: int)->list[Vacancy]:
        pages = await self._get_total_pages(browser,text)
        
        logger.info(f"[job={job_id}] Total pages to scrape: {pages}")
        
        tasks = [
            self.get_list_items(get_browser(),text,i)
            for i in range(pages)
        ]
        results =_flatten_list(await asyncio.gather(*tasks)) 
        
        return results


    async def get_list_items(self, browser,query:str, page_num:int = 0)->list[Vacancy]:
        result:list[Vacancy] = []
        try:
            page = await browser.new_page()
            await page.route("**/*", self._block_resources)
            url = VACANCIES_URL.format(query=quote_plus(query), page=page_num)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            await self._scroll_page(page)
            await page.wait_for_timeout(500)
            cards = await page.evaluate("""
                () => Array.from(document.querySelectorAll('[data-qa^=vacancy-serp__vacancy]'))
                    .map(v => {
                        const title = v.querySelector('[data-qa=serp-item__title-text]')?.textContent || null;
                        
                        const link = v.querySelector('a')?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/(\d+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
            """)
            
            print("for page",page_num, "cards ",len(cards))
            result = [
                Vacancy(name=card['title'],link=card['link'],vacancy_id=card['vacancy_id'])
                for card in cards
            ]
            return result
                
        except Exception as e:
            logger.error(f"Error getting list: {e}")

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

    async def _block_resources(self,route, request):
        if request.resource_type in ("image", "font", "media", "stylesheet"):
            await route.abort()
        else:
            await route.continue_()

    async def _get_total_pages(self,browser, query: str) -> int:
        page = await browser.new_page()
        try:
            await page.route("**/*", self._block_resources)
            url = VACANCIES_URL.format(query=quote_plus(query), page=0)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            pages = await page.query_selector_all('[data-qa="pager-page"]')
            pages_texts = [
                page.inner_text()
                for page in pages
            ]
            max_page = max([int(text) for text in await asyncio.gather(*pages_texts)])
            if max_page:
                try:
                    return min(max_page, HH_MAX_PAGES)
                except ValueError:
                    pass
            return 1
        except Exception as e:
            logger.warning(f"Error getting total pages: {e}")
            return 1
        finally:
            await page.close()





# @time_performance
# async def start():
    
#     await start_browser()
    
#     parser = AutoParserHH()
    
#     vacancy_names = [
#         "backend developer",
#         "PHP developer",
#         "Frontend разработчик"
#     ]
    
#     vacancies_tasks = [parser.get_vacancies_by_name(browser=get_browser(),text=name,job_id=12) for name in vacancy_names]
    
#     result = _flatten_list(await asyncio.gather(*vacancies_tasks))
    
#     print("result ",len(result), result)
    
#     print("finished")
#     await close_browser()
    
    

# asyncio.run(start())
    
