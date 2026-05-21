import asyncio
import logging
import os
import random
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

from playwright.async_api import async_playwright
from sqlmodel import Session, select

from app.database import engine
from app.models.auto_parsed_job import AutoParsedJob
from app.models.parsing_job import ParsingJob

logger = logging.getLogger(__name__)

HH_MAX_PAGES = int(os.getenv("HH_MAX_PAGES", "5"))
LIST_URL = "https://hh.ru/search/vacancy?text={query}&area=1&page={page}"
VACANCY_URL = "https://hh.ru/vacancy/{vacancy_id}"

# Strong references to in-flight parse tasks. asyncio only keeps weak refs to
# tasks, so without this set a running parse can be garbage-collected mid-run.
_background_tasks: set[asyncio.Task] = set()


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


async def _scrape_list_page(browser, query: str, page_num: int, semaphore: asyncio.Semaphore) -> list[tuple[str, str]]:
    async with semaphore:
        page = await browser.new_page()
        try:
            await page.route("**/*", _block_resources)
            url = LIST_URL.format(query=quote_plus(query), page=page_num)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            cards = await page.query_selector_all('[data-qa="vacancy-serp__vacancy"]')
            results = []
            for card in cards:
                text = await card.inner_text()
                if "Вы уже откликнулись" in text:
                    continue
                btn = await card.query_selector('a[data-qa="vacancy-serp__vacancy_response"]')
                if not btn:
                    continue
                href = await btn.get_attribute("href") or ""
                match = re.search(r'vacancyId=(\d+)', href)
                if not match:
                    continue
                vacancy_id = match.group(1)
                title_el = await card.query_selector('[data-qa="serp-item__title-text"]')
                title = (await title_el.inner_text()).strip() if title_el else ""
                results.append((vacancy_id, title))
            return results
        except Exception as e:
            logger.warning(f"Error scraping list page {page_num}: {e}")
            return []
        finally:
            await page.close()
            await asyncio.sleep(random.uniform(1, 5))


async def _get_total_pages(browser, query: str) -> int:
    page = await browser.new_page()
    try:
        await page.route("**/*", _block_resources)
        url = LIST_URL.format(query=quote_plus(query), page=0)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        last_page_el = await page.query_selector('[data-qa="pager-page"]:last-child')
        if last_page_el:
            text = (await last_page_el.inner_text()).strip()
            try:
                return min(int(text), HH_MAX_PAGES)
            except ValueError:
                pass
        return 1
    except Exception as e:
        logger.warning(f"Error getting total pages: {e}")
        return 1
    finally:
        await page.close()


async def _phase1_collect_ids(browser, query: str, job_id: int) -> list[tuple[str, str]]:
    total_pages = await _get_total_pages(browser, query)
    total_pages = min(total_pages, HH_MAX_PAGES)
    logger.info(f"[job={job_id}] Total pages to scrape: {total_pages}")

    semaphore = asyncio.Semaphore(3)
    tasks = [
        _scrape_list_page(browser, query, page_num, semaphore)
        for page_num in range(0, total_pages)
    ]
    results = await asyncio.gather(*tasks)
    seen: set[str] = set()
    all_items: list[tuple[str, str]] = []
    for page_items in results:
        for vacancy_id, title in page_items:
            if vacancy_id not in seen:
                seen.add(vacancy_id)
                all_items.append((vacancy_id, title))
    return all_items


async def _scrape_vacancy(browser, vacancy_id: str, prefetched_title: str, semaphore: asyncio.Semaphore) -> Optional[dict]:
    async with semaphore:
        page = await browser.new_page()
        try:
            await page.route("**/*", _block_resources)
            url = VACANCY_URL.format(vacancy_id=vacancy_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            title_el = await page.query_selector('[data-qa="vacancy-title"]')
            body_el = await page.query_selector('[data-qa="vacancy-description"]')

            detail_title = (await title_el.inner_text()).strip() if title_el else ""
            title = detail_title or prefetched_title or "Unknown"
            body = (await body_el.inner_text()).strip() if body_el else ""

            return {
                "vacancy_id": vacancy_id,
                "url": url,
                "job_title": title,
                "job_text": body,
            }
        except Exception as e:
            logger.warning(f"Error scraping vacancy {vacancy_id}: {e}")
            return None
        finally:
            await page.close()


async def _phase2_fetch_details(browser, vacancy_items: list[tuple[str, str]], job_id: int, user_id: int) -> None:
    semaphore = asyncio.Semaphore(4)

    async def process_one(vacancy_id: str, prefetched_title: str):
        result = await _scrape_vacancy(browser, vacancy_id, prefetched_title, semaphore)
        if result is None:
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
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                vacancy_items = await _phase1_collect_ids(browser, query, job_id)

                with Session(engine) as session:
                    parsing_job = session.get(ParsingJob, job_id)
                    if parsing_job:
                        parsing_job.total_found = len(vacancy_items)
                        session.add(parsing_job)
                        session.commit()

                await _phase2_fetch_details(browser, vacancy_items, job_id, user_id)
            finally:
                await browser.close()

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
