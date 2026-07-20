import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker as DbSession
from app.decorators.time_perf import with_timer
from app.job_parser.hh_parser import Vacancy
from app.models import AutoParsedJob
from app.models.parsing_job import ParsingJob
from app.pw_instances import chromium as chromium_module
from app.services.scraper.parsers.geek_job import GeekJobVacancyParser
from app.services.scraper.parsers.general import GeneralVacancyParser
from app.services.scraper.parsers.hh import HHVacancyParser

logger = logging.getLogger(__name__)


class VacancyScrapingService:
    def __init__(self):
        self._parsers: list[GeneralVacancyParser] = [
            HHVacancyParser(),
            GeekJobVacancyParser(),
        ]

    async def run_parse_job(self, job_id: int, query: str, user_id: int) -> int | None:
        """
        Run a full parse in the background. Progress is persisted to the
        ParsingJob row in the DB; SSE clients read it from there, so the parse is
        fully decoupled from any connected browser and survives page reloads.
        """
        try:
            async with DbSession() as session:
                parsing_job = await session.get(ParsingJob, job_id)
                if parsing_job:
                    parsing_job.status = "running"
                    session.add(parsing_job)
                    await session.commit()

            result: list[Vacancy] = []
            async with with_timer("browser"):
                semaphore = asyncio.Semaphore(4)
                for parser in self._parsers:
                    try:
                        logger.info(f"Started parsing {parser.get_name()}")
                        vacancy_items = await parser.get_list(
                            chromium_module.chromium, query, job_id
                        )
                        result.extend(vacancy_items)
                        async with DbSession() as session:
                            parsing_job = await session.get(ParsingJob, job_id)
                            if parsing_job:
                                parsing_job.total_found = parsing_job.total_found + len(
                                    vacancy_items
                                )
                                await session.commit()

                                results = await asyncio.gather(
                                    *[
                                        self.__parse_single_vacancy(
                                            semaphore,
                                            session,
                                            parser,
                                            vacancy=vacancy,
                                            job_id=job_id,
                                            user_id=user_id,
                                        )
                                        for vacancy in vacancy_items
                                    ],
                                    return_exceptions=True,
                                )
                                await session.commit()

                                for res in results:
                                    if isinstance(res, Exception):
                                        logger.warning(
                                            f"[job={job_id}] Vacancy processing error: {res}"
                                        )
                                    else:
                                        logger.info("item completed")
                    except Exception as e:
                        logger.error(f"[job={job_id}] Parse failed: {e}")
            logger.info(f"total items: {len(result)} {result}")

            async with DbSession() as session:
                parsing_job = await session.get(ParsingJob, job_id)
                if parsing_job:
                    parsing_job.status = "done"
                    parsing_job.finished_at = datetime.utcnow()
                    session.add(parsing_job)
                    await session.commit()
            return parsing_job.id
        except Exception as e:
            logger.error(f"[job={job_id}] Parse failed: {e}")
            async with DbSession() as session:
                parsing_job = await session.get(ParsingJob, job_id)
                if parsing_job:
                    parsing_job.status = "failed"
                    parsing_job.error = str(e)
                    parsing_job.finished_at = datetime.utcnow()
                    session.add(parsing_job)
                    await session.commit()
                    return parsing_job.id

    async def __parse_single_vacancy(
        self,
        semaphore: asyncio.Semaphore,
        session: AsyncSession,
        parser: GeneralVacancyParser,
        vacancy: Vacancy,
        job_id: int,
        user_id: int,
    ):
        async with semaphore:
            parsing_job = await session.get(ParsingJob, job_id)
            page = await chromium_module.chromium.new_page()
            try:
                item = await parser.parse_single_vacancy(
                    page, vacancy_id=vacancy.vacancy_id
                )
                url = parser.get_single_url(vacancy.vacancy_id)

                parsing_job.saved_count += 1
                auto_parsed_job = AutoParsedJob(
                    cover_letter_text="",
                    is_applied=False,
                    job_text=item.job_text,
                    job_title=item.job_title,
                    vacancy_id=vacancy.vacancy_id,
                    parsing_job_id=parsing_job.id,
                    web_site="",
                    user_id=user_id,
                    url=url,
                    is_viewed=False,
                    is_generated=True,
                )
                session.add(auto_parsed_job)
                session.add(parsing_job)
                return item
            except Exception as e:
                raise e
            finally:
                await page.close()
