from sqlmodel import Session
from fastapi import Depends
from app.database import get_db
from app.repository import AutoParseJobRepository
from app.services.scraper.vacancy_scraper import VacancyScrapingService
def get_auto_parse_repository(session: Session = Depends(get_db)) -> AutoParseJobRepository:
    
    return AutoParseJobRepository()


def get_vacancy_scraping_service()->VacancyScrapingService:
    return VacancyScrapingService()