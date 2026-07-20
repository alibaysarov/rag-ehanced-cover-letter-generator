from typing import Annotated

from fastapi import Depends
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repository import AutoParseJobRepository, CVRepository, UserRepository,ProjectRepository
from app.repository.sent_cover_letter_repository import SentCoverLetterRepository
from app.services import (
    CoverLetterService,
    CVService,
    JwtService,
    LetterService,
    PasswordService,
    ProjectStorageService,
    VacancyScrapingService,
    UserService,
)
from app.services.projects import get_projects_service

DBSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(session: AsyncSession = Depends(get_db))->UserRepository:
    return UserRepository(session)


def get_sent_letter_repository(session: AsyncSession = Depends(get_db)) -> SentCoverLetterRepository:
    return SentCoverLetterRepository(session)


def get_project_repository(session: AsyncSession = Depends(get_db)) ->ProjectRepository:
    return ProjectRepository(session)

def get_cv_repository(session: AsyncSession = Depends(get_db)) -> CVRepository:
    """Dependency to get CVRepository with database session"""
    return CVRepository(session)


def get_auto_parse_repository(session: AsyncSession = Depends(get_db)) -> AutoParseJobRepository:
    
    return AutoParseJobRepository(session)


def get_user_service(
    user_repo:UserRepository = Depends(get_user_repository) 
)->UserService:
    return UserService(repo=user_repo)


def get_letter_service(session: AsyncSession = Depends(get_db)) -> LetterService:
    return LetterService(session)


def get_cover_letter_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> CoverLetterService:
    return CoverLetterService(user_repo=user_repo)


def get_cv_service(
    cv_repo: CVRepository = Depends(get_cv_repository)
) -> CVService:
    """Dependency to get CVService instance with database session"""
    return CVService(repo=cv_repo)


def get_jwt_service() -> JwtService:
    return JwtService()


def get_password_service() -> PasswordService:
    return PasswordService()


def get_projects_storage_service() -> ProjectStorageService:
    return get_projects_service()


def get_pdf_reader() -> PDFReader:
    return PDFReader()


def get_sentence_splitter() -> SentenceSplitter:
    return SentenceSplitter(chunk_size=1000, chunk_overlap=0)


def get_vacancy_scraping_service() -> VacancyScrapingService:
    return VacancyScrapingService()