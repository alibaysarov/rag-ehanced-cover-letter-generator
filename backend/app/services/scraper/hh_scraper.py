import asyncio
import json
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

# In-memory SSE queues: job_id -> asyncio.Queue
_progress_queues: dict[int, asyncio.Queue] = {}


def get_or_create_queue(job_id: int) -> asyncio.Queue:
    if job_id not in _progress_queues:
        _progress_queues[job_id] = asyncio.Queue()
    return _progress_queues[job_id]


def remove_queue(job_id: int) -> None:
    _progress_queues.pop(job_id, None)


async def _block_resources(route, request):
    if request.resource_type in ("image", "font", "media", "stylesheet"):
        await route.abort()
    else:
        await route.continue_()


async def _scrape_list_page(browser, query: str, page_num: int, semaphore: asyncio.Semaphore) -> list[str]:
    async with semaphore:
        page = await browser.new_page()
        try:
            await page.route("**/*", _block_resources)
            url = LIST_URL.format(query=quote_plus(query), page=page_num)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            cards = await page.query_selector_all('[data-qa="vacancy-serp__vacancy"]')
            ids = []
            for card in cards:
                text = await card.inner_text()
                if "Вы уже откликнулись" in text:
                    continue
                btn = await card.query_selector('a[data-qa="vacancy-serp__vacancy_response"]')
                if not btn:
                    continue
                href = await btn.get_attribute("href") or ""
                match = re.search(r'vacancyId=(\d+)', href)
                if match:
                    ids.append(match.group(1))
            return ids
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


async def _phase1_collect_ids(browser, query: str, job_id: int) -> list[str]:
    total_pages = await _get_total_pages(browser, query)
    total_pages = min(total_pages, HH_MAX_PAGES)
    logger.info(f"[job={job_id}] Total pages to scrape: {total_pages}")

    semaphore = asyncio.Semaphore(3)
    tasks = [
        _scrape_list_page(browser, query, page_num, semaphore)
        for page_num in range(0, total_pages)
    ]
    results = await asyncio.gather(*tasks)
    all_ids = []
    seen = set()
    for page_ids in results:
        for vid in page_ids:
            if vid not in seen:
                seen.add(vid)
                all_ids.append(vid)
    return all_ids


async def _scrape_vacancy(browser, vacancy_id: str, job_id: int, user_id: int, semaphore: asyncio.Semaphore) -> Optional[dict]:
    async with semaphore:
        page = await browser.new_page()
        try:
            await page.route("**/*", _block_resources)
            url = VACANCY_URL.format(vacancy_id=vacancy_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            title_el = await page.query_selector('[data-qa="vacancy-title"]')
            body_el = await page.query_selector('[data-qa="vacancy-description"]')

            title = (await title_el.inner_text()).strip() if title_el else "Unknown"
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


async def _phase2_fetch_details(browser, vacancy_ids: list[str], job_id: int, user_id: int) -> None:
    semaphore = asyncio.Semaphore(4)
    queue = get_or_create_queue(job_id)

    async def process_one(vacancy_id: str):
        result = await _scrape_vacancy(browser, vacancy_id, job_id, user_id, semaphore)
        if result is None:
            return
        with Session(engine) as session:
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

            saved = parsing_job.saved_count if parsing_job else 0
            total = parsing_job.total_found if parsing_job else len(vacancy_ids)

        await queue.put(json.dumps({
            "saved_count": saved,
            "total_found": total,
            "status": "running",
        }))

    await asyncio.gather(*[process_one(vid) for vid in vacancy_ids])


async def run_parse_job(job_id: int, query: str, user_id: int) -> None:
    queue = get_or_create_queue(job_id)

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
                vacancy_ids = await _phase1_collect_ids(browser, query, job_id)

                with Session(engine) as session:
                    parsing_job = session.get(ParsingJob, job_id)
                    if parsing_job:
                        parsing_job.total_found = len(vacancy_ids)
                        session.add(parsing_job)
                        session.commit()

                await queue.put(json.dumps({
                    "saved_count": 0,
                    "total_found": len(vacancy_ids),
                    "status": "running",
                }))

                await _phase2_fetch_details(browser, vacancy_ids, job_id, user_id)
            finally:
                await browser.close()

        with Session(engine) as session:
            parsing_job = session.get(ParsingJob, job_id)
            if parsing_job:
                parsing_job.status = "done"
                parsing_job.finished_at = datetime.utcnow()
                session.add(parsing_job)
                session.commit()
                saved = parsing_job.saved_count
                total = parsing_job.total_found

        await queue.put(json.dumps({
            "saved_count": saved,
            "total_found": total,
            "status": "done",
        }))

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
        await queue.put(json.dumps({
            "saved_count": 0,
            "total_found": 0,
            "status": "failed",
        }))
    finally:
        # Signal SSE stream to close
        await queue.put(None)
