from abc import abstractmethod
from app.job_parser.hh_parser import Vacancy
from app.decorators.browser import pw_browser,managed_page
from app.services.scraper.parsers.general import GeneralVacancyParser
from app.pw_instances import chromium as chromium_module
from sqlmodel import Session
from datetime import datetime
from app.models.parsing_job import ParsingJob
from app.decorators.time_perf import with_timer
from app.database import engine
from app.pw_instances import chromium as chromium_module
from app.services.scraper.parsers.hh import HHVacancyParser
from app.services.scraper.parsers.geek_job import GeekJobVacancyParser
from app.helper.flatten_list import flatten_list
import logging


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
                for parser in self._parsers:
                    try:
                        logger.info(f"Started parsing {parser.get_name()}")
                        vacancy_items = await parser.get_list(chromium_module.chromium,query,job_id)
                        result.append(vacancy_items)
                        with Session(engine) as session:
                            parsing_job = session.get(ParsingJob, job_id)
                            if parsing_job:
                                parsing_job.total_found = parsing_job.total_found + len(vacancy_items)
                                session.add(parsing_job)
                                session.commit()
                    except Exception as e:
                        logger.error(f"[job={job_id}] Parse failed: {e}")
                result = flatten_list(result)
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