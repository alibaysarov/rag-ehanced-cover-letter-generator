import asyncio
import logging
from datetime import datetime

from sqlmodel import Session

from app.database import engine
from app.decorators.time_perf import with_timer
from app.job_parser.hh_parser import Vacancy
from app.models.parsing_job import ParsingJob
from app.pw_instances import chromium as chromium_module
from app.services.scraper.parsers.geek_job import GeekJobVacancyParser
from app.services.scraper.parsers.general import GeneralVacancyParser
from app.services.scraper.parsers.hh import HHVacancyParser

logger = logging.getLogger(__name__)


class VacancyScrapingService:
    def __init__(self):
        self._parsers:list[GeneralVacancyParser] = [
            HHVacancyParser(),
            GeekJobVacancyParser(),
        ]
        
    
        
    async def run_parse_job(self,job_id: int, query: str, user_id: int) -> None:
        """
        Run a full parse in the background. Progress is persisted to the
        ParsingJob row in the DB; SSE clients read it from there, so the parse is
        fully decoupled from any connected browser and survives page reloads.
        """
        try:
            with Session(engine) as session:
                parsing_job = session.get(ParsingJob, job_id)
                if parsing_job:
                    parsing_job.status = "running"
                    session.add(parsing_job)
                    session.commit()

            result:list[Vacancy] = []
            async with with_timer("browser"):
                semaphore = asyncio.Semaphore(4)
                for parser in self._parsers:
                    try:
                        logger.info(f"Started parsing {parser.get_name()}")
                        vacancy_items = await parser.get_list(chromium_module.chromium,query,job_id)
                        result.extend(vacancy_items)
                        with Session(engine) as session:
                            parsing_job = session.get(ParsingJob, job_id)
                            if parsing_job:
                                parsing_job.total_found = parsing_job.total_found + len(vacancy_items)
                                session.commit()
                                
                                results = await asyncio.gather(
                                    *[self._parse_single_vacancy(semaphore,session,parser, vacancy=vacancy,job_id=job_id) for vacancy in vacancy_items[0:10]],
                                    return_exceptions=True,
                                )
                                session.commit()
                                
                                for res in results:
                                    if isinstance(res, Exception):
                                        logger.warning(f"[job={job_id}] Vacancy processing error: {res}")
                                    else:
                                        logger.info("item completed",res)
                    except Exception as e:
                        logger.error(f"[job={job_id}] Parse failed: {e}")
            logger.info(f"total items: {len(result)} {result}")
            
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
    
    
    async def _parse_single_vacancy(self,semaphore:asyncio.Semaphore,session:Session,parser:GeneralVacancyParser,vacancy:Vacancy,job_id:int):
        async with semaphore:
            parsing_job = session.get(ParsingJob, job_id)
            page = await chromium_module.chromium.new_page()
            try:
                item = await parser.parse_single_vacancy(page,vacancy_id=vacancy.vacancy_id)
                parsing_job.saved_count +=1
                session.add(parsing_job)
                return item
            except Exception as e:
                raise e
            finally:
                await page.close()