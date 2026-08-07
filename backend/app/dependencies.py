from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands import GenerateCoverCommandLetterHandler, build_handler
from app.database import get_db
from app.repository import (
    AutoParseJobRepository,
    CVRepository,
    ProjectRepository,
    UserRepository,
)
from app.repository.sent_cover_letter_repository import SentCoverLetterRepository
from app.services import (
    CVService,
    JwtService,
    LetterService,
    PasswordService,
    ProjectStorageService,
    UserService,
    VacancyScrapingService,
)
from app.services.cover_letter import CoverLetterService
from app.services.websocket.websocket_manager import WebSocketManager
from app.tasks.listener.pubsub_listener import PubsubListener

DBSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_sent_letter_repository(
    session: AsyncSession = Depends(get_db),
) -> SentCoverLetterRepository:
    return SentCoverLetterRepository(session)


def get_project_repository(
    session: AsyncSession = Depends(get_db),
) -> ProjectRepository:
    return ProjectRepository(session)


def get_cv_repository(session: AsyncSession = Depends(get_db)) -> CVRepository:
    """Dependency to get CVRepository with database session"""
    return CVRepository(session)


def get_auto_parse_repository(
    session: AsyncSession = Depends(get_db),
) -> AutoParseJobRepository:

    return AutoParseJobRepository(session)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repo=user_repo)


def get_letter_service(session: AsyncSession = Depends(get_db)) -> LetterService:
    return LetterService(session)


async def get_generate_letter_handler(
    session: AsyncSession = Depends(get_db),
) -> GenerateCoverCommandLetterHandler:
    return build_handler(session)


def get_vacancy_scraping_service() -> VacancyScrapingService:
    return VacancyScrapingService()


def get_cover_letter_service(
    user_repo: UserRepository = Depends(get_user_repository),
    project_repository: ProjectRepository = Depends(get_project_repository),
    auto_parse_job_repository: AutoParseJobRepository = Depends(
        get_auto_parse_repository
    ),
    generate_cover_letter_command_handler: GenerateCoverCommandLetterHandler = Depends(
        get_generate_letter_handler
    ),
    vacancy_scraping_service: VacancyScrapingService = Depends(
        get_vacancy_scraping_service
    ),
) -> CoverLetterService:
    return CoverLetterService(
        user_repo=user_repo,
        project_repository=project_repository,
        auto_parse_job_repository=auto_parse_job_repository,
        generate_cover_letter_command_handler=generate_cover_letter_command_handler,
        vacancy_scraping_service=vacancy_scraping_service,
    )


def get_cv_service(cv_repo: CVRepository = Depends(get_cv_repository)) -> CVService:
    """Dependency to get CVService instance with database session"""
    return CVService(repo=cv_repo)


def get_jwt_service() -> JwtService:
    return JwtService()


def get_password_service() -> PasswordService:
    return PasswordService()


def get_projects_storage_service(
    project_repository: ProjectRepository = Depends(get_project_repository),
) -> ProjectStorageService:
    return ProjectStorageService(project_repository)


def get_pdf_reader() -> PDFReader:
    return PDFReader()


def get_sentence_splitter() -> SentenceSplitter:
    return SentenceSplitter(chunk_size=1000, chunk_overlap=0)


# ws
@lru_cache
def get_websocket_manager() -> WebSocketManager:
    return WebSocketManager()


# redis listener
@lru_cache
def get_pub_sub_listener() -> PubsubListener:
    return PubsubListener()
