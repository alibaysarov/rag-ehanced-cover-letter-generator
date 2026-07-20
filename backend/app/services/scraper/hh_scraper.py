import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from playwright.async_api import Page
from sqlmodel import Session, select

from app.database import engine
from app.decorators.time_perf import with_timer
from app.models.auto_parsed_job import AutoParsedJob
from app.models.parsing_job import ParsingJob
from app.pw_instances import chromium as chromium_module

logger = logging.getLogger(__name__)

HH_MAX_PAGES = int(os.getenv("HH_MAX_PAGES", "5"))
LIST_URL = "https://hh.ru/search/vacancy?text={query}&area=1&page={page}&items_on_page=100"
VACANCY_URL = "https://hh.ru/vacancy/{vacancy_id}"

# Strong references to in-flight parse tasks. asyncio only keeps weak refs to
# tasks, so without this set a running parse can be garbage-collected mid-run.
_background_tasks: set[asyncio.Task] = set()


def get_company_url(url:str):
        if url.startswith("https://hh.ru"):
            return url
        return f"https://hh.ru{url}"

def launch_parse_job(job_id: int, query: str, user_id: int) -> None:
    """Start a parse in the background and keep a strong reference to it so it
    survives garbage collection and page reloads."""
    task = asyncio.create_task(run_parse_job(job_id, query, user_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _block_resources(route, request):
    if request.resource_type in ("image", "font", "media", "stylesheet"):
        await route.abort()
    else:
        await route.continue_()


from app.job_parser.hh_parser import AutoParserHH

hh_parser = AutoParserHH()

async def _get_list(browser, query: str, job_id: int)-> list[tuple[str, str]]:
    results = await hh_parser.get_vacancies_by_name(browser,query,job_id=job_id)
    seen: set[str] = set()
    all_items: list[tuple[str, str]] = []
    for item in results:
        if item.vacancy_id not in seen:
            seen.add(item.vacancy_id)
            all_items.append((item.vacancy_id,item.name))
        
    return all_items


async def _scrape_vacancy(browser, vacancy_id: str, prefetched_title: str, semaphore: asyncio.Semaphore) -> Optional[dict]:
    
    async def _get_content_pw(page:Page)->dict:
        title_el = await page.query_selector('[data-qa="vacancy-title"]')
        body_el = await page.query_selector('[data-qa="vacancy-description"]')

        detail_title = (await title_el.inner_text()).strip() if title_el else ""
        title = detail_title or prefetched_title or "Unknown"
        body = (await body_el.inner_text()).strip() if body_el else ""
        
        vacancy_el = await page.query_selector('a[data-qa="vacancy-company-name"]')
        vacancy_url = (await vacancy_el.get_attribute("href")) if vacancy_el else ""
        
        vacancy_item = {
            "vacancy_id": vacancy_id,
            "url": url,
            "job_title": title,
            "job_text": body.strip(),
            "vacancy_url": get_company_url(vacancy_url) if vacancy_url else ""
        }
        
        return vacancy_item
        
        
    async def _get_content_js(page:Page)->dict:
        
        vacancy_item = await page.evaluate("""
            () =>{
                
                const titleEl = document.querySelector('[data-qa="vacancy-title"]');
                if(!titleEl) {
                    return null;
                }
                
                const bodyEl =  document.querySelector('[data-qa="vacancy-description"]');
                
                if(!bodyEl) {
                    return null;
                }
                
                const companyEl = document.querySelector('a[data-qa="vacancy-company-name"]');
                
                const title = titleEl.innerText.trim() ?? '';
                const body = bodyEl.innerText.trim() ?? '';
                const companyUrl = companyEl?.href ?? '';
                
                return {
                    "job_title": title,
                    "job_text": body,
                    "vacancy_url": companyUrl ?? '',
                }
            
            }
        """)
        
        vacancy_item['vacancy_id'] = vacancy_id
        vacancy_item['url'] = url
        
        return vacancy_item
        
    async with semaphore:
        page = await browser.new_page()
        try:
            await page.route("**/*", _block_resources)
            url = VACANCY_URL.format(vacancy_id=vacancy_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            result = await _get_content_js(page=page)
            
            return result
        except Exception as e:
            logger.warning(f"Error scraping vacancy with js {vacancy_id}: {e}")
            try:
                pw_item = await _get_content_pw(page=page)
                return pw_item
            except Exception as e:
                logger.warning(f"Error scraping vacancy from pw {vacancy_id}: {e}")
                return None
            finally:
                await page.close()
        finally:
            await page.close()


async def _phase2_fetch_details(browser, vacancy_items: list[tuple[str, str]], job_id: int, user_id: int) -> None:
    semaphore = asyncio.Semaphore(4)
    
    async def process_one(vacancy_id: str, prefetched_title: str):
        result = await _scrape_vacancy(browser, vacancy_id, prefetched_title, semaphore)
        
        if result is None:
            logger.info(f"vacancy with {vacancy_id} is None")
            return
        with Session(engine) as session:
            existing = session.exec(
                select(AutoParsedJob).where(
                    AutoParsedJob.user_id == user_id,
                    AutoParsedJob.vacancy_id == result["vacancy_id"],
                )
            ).first()
            if existing:
                return

            job_row = AutoParsedJob(
                user_id=user_id,
                parsing_job_id=job_id,
                vacancy_id=result["vacancy_id"],
                url=result["url"],
                job_title=result["job_title"],
                job_text=result["job_text"],
                web_site=result["vacancy_url"]
            )
            session.add(job_row)

            parsing_job = session.get(ParsingJob, job_id)
            if parsing_job:
                parsing_job.saved_count += 1
                session.add(parsing_job)
            session.commit()

    # return_exceptions=True so one failed vacancy never aborts the whole parse.
    results = await asyncio.gather(
        *[process_one(vid, title) for vid, title in vacancy_items],
        return_exceptions=True,
    )
    for res in results:
        if isinstance(res, Exception):
            logger.warning(f"[job={job_id}] Vacancy processing error: {res}")


async def run_parse_job(job_id: int, query: str, user_id: int) -> None:
    """Run a full parse in the background. Progress is persisted to the
    ParsingJob row in the DB; SSE clients read it from there, so the parse is
    fully decoupled from any connected browser and survives page reloads."""
    with Session(engine) as session:
        parsing_job = session.get(ParsingJob, job_id)
        if parsing_job:
            parsing_job.status = "running"
            session.add(parsing_job)
            session.commit()

    try:
        async with with_timer("browser"):
            vacancy_items = await _get_list(chromium_module.chromium,query,job_id)
            with Session(engine) as session:
                parsing_job = session.get(ParsingJob, job_id)
                if parsing_job:
                    parsing_job.total_found = len(vacancy_items)
                    session.add(parsing_job)
                    session.commit()

            await _phase2_fetch_details(chromium_module.chromium, vacancy_items, job_id, user_id)

        with Session(engine) as session:
            parsing_job = session.get(ParsingJob, job_id)
            if parsing_job:
                parsing_job.status = "done"
                parsing_job.finished_at = datetime.utcnow()
                session.add(parsing_job)
                session.commit()

    except Exception as e:
        logger.error(f"[job={job_id}] Parse failed: {e}")
        with Session(engine) as session:
            parsing_job = session.get(ParsingJob, job_id)
            if parsing_job:
                parsing_job.status = "failed"
                parsing_job.error = str(e)
                parsing_job.finished_at = datetime.utcnow()
                session.add(parsing_job)
                session.commit()
