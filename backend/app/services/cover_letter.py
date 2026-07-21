import asyncio
import json
import logging
import re
from typing import Any

from app.cache import redis as redis_db
from app.commands import GenerateCoverCommandLetterHandler, GenerateLetterCommand
from app.models import AutoParsedJob, Project, User
from app.repository import AutoParseJobRepository, ProjectRepository
from app.repository.user_repository import UserRepository
from app.schemas.llm_outputs.relevant_projects import RelevantProject
from app.services.llm.agents.tools.fetch_url import parse_hh
from app.services.llm.cover_letter_prompt import CoverLetterPrompt
from app.services.llm.relevant_projects import RelevantProjectsPrompt
from app.services.scraper.vacancy_scraper import VacancyScrapingService

from ..schemas.llm_outputs.job_requirements import JobRequirement
from ..services.llm.job_requirements import JobParsePrompt

logger = logging.getLogger(__name__)


class CoverLetterService:
    def __init__(
        self,
        user_repo: UserRepository,
        project_repository: ProjectRepository,
        auto_parse_job_repository: AutoParseJobRepository,
        generate_cover_letter_command_handler: GenerateCoverCommandLetterHandler,
        vacancy_scraping_service: VacancyScrapingService,
    ):
        # Services
        self.vacancy_scraping_service = vacancy_scraping_service
        # Commands
        self.generate_cover_letter_command_handler = (
            generate_cover_letter_command_handler
        )

        # Repos
        self.project_repository = project_repository
        self.user_repo = user_repo
        self.auto_parse_job_repository = auto_parse_job_repository

        # LLM prompts
        self.cover_letter_prompt = CoverLetterPrompt()
        self.job_parse_promt = JobParsePrompt()
        self.relevant_projects_prompt = RelevantProjectsPrompt()

    async def sync_by_url(self, url: str, user_id: int):
        chain = (
            self.cover_letter_prompt.prompt_template
            | self.cover_letter_prompt.get_model
        )
        body = await self.__get_data_from_url(url, user_id)
        result = await chain.ainvoke(body)
        return result.content

    async def stream_by_text(
        self, vacancy_name: str, vacancy_text: str, user: User, lang: str | None = None
    ):

        create_vacancy_dto = {
            "user_id": user.id,
            "parsing_job_id": None,
            "vacancy_id": None,
            "url": "",
            "job_title": vacancy_name,
            "job_text": vacancy_text,
            "is_applied": False,
            "is_viewed": False,
            "cover_letter_text": "",
        }

        auto_parse_job: AutoParsedJob = await self.auto_parse_job_repository.create(
            **create_vacancy_dto
        )

        cover_letter_text = await self.generate_by_vacancy(
            auto_parse_job.id, first_name=user.first_name, last_name=user.last_name
        )

        async for delta in self._clean_stream(cover_letter_text):
            yield delta

    async def stream_by_url(self, url: str, user: User):
        try:
            single_vacancy = await self.vacancy_scraping_service.parse_single(url)
            create_vacancy_dto = {
                "user_id": user.id,
                "parsing_job_id": None,
                "vacancy_id": None,
                "url": url,
                "job_title": single_vacancy.job_title,
                "job_text": single_vacancy.job_text,
                "is_applied": False,
                "is_viewed": False,
                "cover_letter_text": "",
            }

            auto_parse_job: AutoParsedJob = await self.auto_parse_job_repository.create(
                **create_vacancy_dto
            )
            cover_letter_text = await self.generate_by_vacancy(
                auto_parse_job.id, first_name=user.first_name, last_name=user.last_name
            )

            async for delta in self._clean_stream(cover_letter_text):
                yield delta
        except Exception as e:
            print(f"URL parse error: {e}")
            yield "__URL_PARSE_ERROR__"
            return

    # Patterns stripped from the very start of LLM output
    _STRIP_LABEL = re.compile(
        r"^\s*(сообщение|письмо|текст\s+письма|ответ|вот\s+письмо)[:\-]?\s*\n*",
        re.IGNORECASE,
    )

    async def generate_by_vacancy(
        self, vacancy_id: int, first_name: str, last_name: str
    ) -> str:

        command = GenerateLetterCommand(
            first_name=first_name,
            last_name=last_name,
            vacancy_id=vacancy_id,
            batch_id=None,
        )

        cover_letter_text: str = (
            await self.generate_cover_letter_command_handler.handle(command=command)
        )
        return cover_letter_text

    async def _clean_stream(self, text: str):
        #  body: dict
        # result = await (self.cover_letter_prompt.prompt_template | self.cover_letter_prompt.get_model).ainvoke(body)
        # text = result.content
        text = self._STRIP_LABEL.sub("", text).lstrip("\n ")

        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]
            await asyncio.sleep(0.02)

    @staticmethod
    def _chunk_to_text(chunk) -> str:
        """Normalize a stream chunk (str | list | dict | None) to plain text."""
        if chunk is None:
            return ""
        if isinstance(chunk, str):
            return chunk
        if isinstance(chunk, list):
            parts = []
            for part in chunk:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    parts.append(part.get("text", "") or "")
                else:
                    text_attr = getattr(part, "text", None)
                    if text_attr:
                        parts.append(text_attr)
            return "".join(parts)
        if isinstance(chunk, dict):
            return chunk.get("text", "") or ""
        # fallback for objects with a `.content` or `.text` attribute
        text_attr = getattr(chunk, "text", None) or getattr(chunk, "content", None)
        return text_attr if isinstance(text_attr, str) else ""

    async def __get_data_from_text(self, text: str, user_id: int):
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement = await chain.ainvoke({"job_text": text})

        ranked = await self._get_ranked_projects(user_id, text, vacancy)

        user = self.user_repo.get_user_by_id(user_id)
        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name": vacancy.name,
            "lang": "ru",
            "project_name": vacancy.name,
            "user_projects": user_projects,
            "vacancy_requirements": vacancy.technologies,
            "vacancy_technologies": vacancy.technologies,
            "user_first_name": (user.first_name or "") if user else "",
            "user_last_name": (user.last_name or "") if user else "",
        }
        return body

    async def _get_ranked_projects(
        self, user_id, vacancy_text: str, job_requirement: JobRequirement
    ):

        relevant_projects = await self.project_repository.get_relevant(
            user_id, job_requirement.technologies
        )

        if len(relevant_projects) > 2:
            relevant_project_promt = RelevantProjectsPrompt()
            model_response = relevant_project_promt.get_sync_response(
                {
                    "job_text": vacancy_text,
                    "technologies": job_requirement.technologies,
                    "projects": relevant_projects,
                }
            )
            projects = model_response.projects
            result = []

            for project in projects:
                relevant_projects
                item = next(
                    (
                        item
                        for item, _ in relevant_projects
                        if str(item.id) == str(project.id)
                    ),
                    None,
                )
                if item is not None:
                    result.append(item)
            return result

        return [project for project, _ in relevant_projects]

    async def __get_data_from_url(self, url: str, user: User):

        text = await self.__fetch_from_browser(url)
        job_parse = JobParsePrompt()
        chain = job_parse.prompt_template | job_parse.get_model
        vacancy: JobRequirement = chain.invoke({"job_text": text})

        create_vacancy_dto = {
            "user_id": user.id,
            "parsing_job_id": None,
            "vacancy_id": None,
            "url": "",
            "job_title": vacancy.jo,
            "job_text": vacancy_text,
            "is_applied": False,
            "is_viewed": False,
            "cover_letter_text": "",
        }

        self.auto_parse_job_repository.create()
        ranked = await self._get_ranked_projects(
            user_id=user.id, vacancy_text=text, job_requirement=vacancy
        )

        user_projects = self.__projects_normalize(ranked=ranked)
        body = {
            "name": vacancy.name,
            "lang": vacancy.lang,
            "project_name": vacancy.project_name,
            "user_projects": user_projects,
            "vacancy_requirements": vacancy.requirements,
            "vacancy_technologies": vacancy.technologies,
            "user_first_name": (user.first_name or "") if user else "",
            "user_last_name": (user.last_name or "") if user else "",
        }
        return body

    async def __fetch_from_browser(self, url: str):
        if await redis_db.redis_client.get(url) is None:
            text = await parse_hh(url)
            await redis_db.redis_client.set(url, text, ex=3600)
        else:
            text = await redis_db.redis_client.get(url)
        return text

    def __projects_normalize(self, ranked: list[Project]) -> str:
        result = [
            {
                "project_name": item.name,
                "skills": item.skills,
                "achievements": item.achievements,
                "technologies": item.technologies,
            }
            for item in ranked
        ]
        return json.dumps(result, ensure_ascii=False, indent=2)

    async def __generate_cover_letter(
        self,
        name: str,
        last_name: str,
        vacancy_name: str,
        vacancy_technologies: list,
        vacancy_requirements: list,
        projects: list,
    ) -> dict:
        cover_letter_body = {
            "user_first_name": name,
            "user_last_name": last_name,
            "lang": "ru",
            "name": vacancy_name,
            "vacancy_technologies": vacancy_technologies,
            "vacancy_requirements": vacancy_requirements,
            "user_projects": projects,
        }
        cover_letter = await self.cover_letter_prompt.get_async_response(
            cover_letter_body
        )
        return cover_letter.content

    async def __sort_projects_llm(self, vacancy, technologies, relevant_projects):
        body = {
            "job_text": vacancy.job_text,
            "technologies": technologies,
            "projects": relevant_projects,
        }
        llm_sorted_projects = await self.relevant_projects_prompt.get_async_response(
            body
        )

        return self.__sort_by_ids(relevant_projects, llm_sorted_projects.projects)

    def __sort_by_ids(
        self,
        projects: list[tuple[Project, Any]] | list[Project],
        llm_projects: list[RelevantProject],
    ) -> list:
        if len(projects) == 0:
            return []
        if isinstance(projects[0], tuple):
            map_ = {item[0].id: item[0] for item in projects}
        else:
            map_ = {item.id: item for item in projects}
        sorted_projects = []
        for llm_project in llm_projects:
            project = map_.get(llm_project.id)
            if project is None:
                logger.warning(
                    f"LLM returned unknown project id {llm_project.id}, skipping"
                )
                continue
            sorted_projects.append(project)

        missing_ids = set(map_.keys()) - {p.id for p in sorted_projects}
        for missing_id in missing_ids:
            logger.warning(f"LLM omitted project id {missing_id}, appending at end")
            sorted_projects.append(map_[missing_id])

        return sorted_projects
