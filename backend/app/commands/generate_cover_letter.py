import logging
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project
from app.repository import AutoParseJobRepository, ProjectRepository, UserRepository
from app.schemas.llm_outputs import RelevantProject
from app.services.llm import CoverLetterPrompt, JobParsePrompt, RelevantProjectsPrompt

logger = logging.getLogger(__name__)

_cover_letter_prompt = CoverLetterPrompt()
_job_parse_prompt = JobParsePrompt()
_relevant_projects_prompt = RelevantProjectsPrompt()


class GenerateLetterCommand(BaseModel):
    vacancy_id: int
    first_name: str
    last_name: str
    batch_id: str | None = None

    model_config = {"frozen": True}


class GenerateCoverCommandLetterHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        project_repository: ProjectRepository,
        auto_parse_job_repository: AutoParseJobRepository,
        cover_letter_prompt: CoverLetterPrompt,
        job_parse_prompt: JobParsePrompt,
        relevant_projects_prompt: RelevantProjectsPrompt,
    ):
        self.user_repo = user_repo
        self.project_repository = project_repository
        self.auto_parse_job_repository = auto_parse_job_repository
        self.cover_letter_prompt = cover_letter_prompt
        self._job_parse_prompt = job_parse_prompt
        self.relevant_projects_prompt = relevant_projects_prompt

    async def handle(self, command: GenerateLetterCommand) -> str:
        logger.info(f"Starting single generation: id {command.vacancy_id}")

        vacancy = await self.auto_parse_job_repository.get_by_id(command.vacancy_id)
        if vacancy is not None:
            user_id = vacancy.user_id
            prep_str = f"{vacancy.id} {vacancy.job_title} {vacancy.job_text}"
            try:
                job_requirement = await self.__extract_job_requirement(prep_str)

                (
                    technologies,
                    relevant_projects,
                ) = await self.__extract_relevant_projects(user_id, job_requirement)

                if len(relevant_projects) == 0:
                    logger.warning(
                        f"Missed getting relevant projects vacancy_id {vacancy.id}\n Technologies:{technologies} \n fetching all projects by user"
                    )
                    user_projects = await self.project_repository.get_by_user(user_id)
                    sorted_projects = await self.__sort_projects_llm(
                        vacancy, technologies, user_projects
                    )

                if len(relevant_projects) > 2:
                    sorted_projects = await self.__sort_projects_llm(
                        vacancy, technologies, relevant_projects
                    )
                    cover_letter: str = await self.__generate_cover_letter(
                        name=command.first_name,
                        last_name=command.last_name,
                        vacancy_name=vacancy.job_title,
                        vacancy_technologies=technologies,
                        vacancy_requirements=technologies,
                        projects=sorted_projects,
                    )
                    await self.auto_parse_job_repository.update_vacancy(
                        vacancy.id, cover_letter, is_generated=True
                    )

                    return cover_letter
                else:
                    cover_letter = await self.__generate_cover_letter(
                        name=command.first_name,
                        last_name=command.last_name,
                        vacancy_name=vacancy.job_title,
                        vacancy_technologies=technologies,
                        vacancy_requirements=technologies,
                        projects=relevant_projects,
                    )
                    print("Response\n", cover_letter)
                    await self.auto_parse_job_repository.update_vacancy(
                        vacancy.id, cover_letter, is_generated=True
                    )

                    return cover_letter
            except Exception as e:
                raise
        else:
            return ""

    async def __extract_relevant_projects(self, user_id, job_requirement):
        technologies = [tech.lower() for tech in job_requirement.technologies]
        relevant_projects = await self.project_repository.get_relevant(
            user_id, technologies
        )

        return technologies, relevant_projects

    async def __extract_job_requirement(self, prep_str):
        job_requirement = await self._job_parse_prompt.get_async_response(
            {"job_text": prep_str}
        )

        return job_requirement

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


def build_handler(session: AsyncSession) -> GenerateCoverCommandLetterHandler:
    """
    Собирает GenerateLetterCommandHandler с репозиториями,
    привязанными к переданной сессии БД.

    Используется и в Celery-таске (внутри async with async_session_maker()),
    и в контроллере (через FastAPI Depends), чтобы не дублировать сборку.
    """
    return GenerateCoverCommandLetterHandler(
        user_repo=UserRepository(session=session),
        project_repository=ProjectRepository(session=session),
        auto_parse_job_repository=AutoParseJobRepository(session=session),
        cover_letter_prompt=_cover_letter_prompt,
        job_parse_prompt=_job_parse_prompt,
        relevant_projects_prompt=_relevant_projects_prompt,
    )
