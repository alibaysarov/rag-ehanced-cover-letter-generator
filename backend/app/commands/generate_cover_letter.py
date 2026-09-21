import logging

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ParsingJob
from app.repository import AutoParseJobRepository, ProjectRepository, UserRepository
from app.schemas.generation_mode import GenerationMode
from app.services.llm import CoverLetterPrompt
from app.services.template_cover_letter import (
    TemplateProject,
    generate_template_cover_letter,
)

logger = logging.getLogger(__name__)


class GenerateLetterCommand(BaseModel):
    vacancy_id: int | str
    first_name: str = ""
    last_name: str = ""
    batch_id: str | int | None = None
    generation_mode: GenerationMode = GenerationMode.AI
    model_config = {"frozen": True}


class GenerateCoverCommandLetterHandler:
    """Loads a single shared context then chooses an AI or pure-template writer."""

    def __init__(
        self,
        user_repo: UserRepository,
        project_repository: ProjectRepository,
        auto_parse_job_repository: AutoParseJobRepository,
        session: AsyncSession,
    ):
        self.user_repo = user_repo
        self.project_repository = project_repository
        self.auto_parse_job_repository = auto_parse_job_repository
        self._session = session
        self._cover_letter_prompt: CoverLetterPrompt | None = None

    async def handle(self, command: GenerateLetterCommand) -> str:
        if not isinstance(command.vacancy_id, int):
            raise LookupError(f"Vacancy {command.vacancy_id} does not exist")
        vacancy = await self.auto_parse_job_repository.get_by_id(command.vacancy_id)
        if vacancy is None:
            raise LookupError(f"Vacancy {command.vacancy_id} does not exist")
        if vacancy.id is None:
            raise RuntimeError("Persisted vacancy is missing an id")
        mode = command.generation_mode
        if vacancy.parsing_job_id is not None:
            parent = await self._session.get(ParsingJob, vacancy.parsing_job_id)
            if parent is None:
                raise LookupError(
                    f"Parsing job {vacancy.parsing_job_id} does not exist"
                )
            mode = parent.generation_mode

        projects = await self.project_repository.get_projects_by_vacancy_text(
            f"{vacancy.job_title}\n{vacancy.job_text}", vacancy.user_id
        )
        if not projects:
            projects = await self.project_repository.get_by_user(vacancy.user_id)

        if mode == GenerationMode.TEMPLATE:
            letter = generate_template_cover_letter(
                vacancy_id=vacancy.id,
                job_title=vacancy.job_title,
                job_text=vacancy.job_text,
                projects=[
                    TemplateProject(p.id, p.name, tuple(p.technologies or []))
                    for p in projects
                    if p.id is not None
                ],
            )
        else:
            technologies = list(
                dict.fromkeys(t for p in projects for t in (p.technologies or []))
            )
            if self._cover_letter_prompt is None:
                self._cover_letter_prompt = CoverLetterPrompt()
            response = await self._cover_letter_prompt.get_async_response(
                {
                    "user_first_name": command.first_name,
                    "user_last_name": command.last_name,
                    "lang": "ru",
                    "name": vacancy.job_title,
                    "vacancy_technologies": technologies,
                    "vacancy_requirements": technologies,
                    "user_projects": projects,
                }
            )
            letter = response.content
        if not isinstance(letter, str) or not letter.strip():
            raise ValueError("Cover-letter generator returned an empty result")
        await self.auto_parse_job_repository.update_vacancy(
            vacancy.id, letter, is_generated=True
        )
        return letter


def build_handler(session: AsyncSession) -> GenerateCoverCommandLetterHandler:
    return GenerateCoverCommandLetterHandler(
        user_repo=UserRepository(session=session),
        project_repository=ProjectRepository(session=session),
        auto_parse_job_repository=AutoParseJobRepository(session=session),
        session=session,
    )
