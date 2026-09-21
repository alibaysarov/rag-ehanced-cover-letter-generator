import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.cache.redis import async_client
from app.dependencies import DBSession, get_project_service
from app.helper import CurrentUser
from app.schemas.llm_outputs.job_requirements import JobRequirement
from app.services import ProjectStorageService
from app.services.llm.job_requirements import JobParsePrompt
from app.services.scraper.vacancy_scraper import VacancyScrapingService

logger = logging.getLogger(__name__)
router = APIRouter()


class ParseDto(BaseModel):
    url: str


@router.post("")
async def parse(
    user: CurrentUser,
    body: ParseDto,
    db: DBSession,
    projects_service: ProjectStorageService = Depends(get_project_service),
):

    vacancy_page = await VacancyScrapingService(db, async_client).parse_single(
        body.url, user.id
    )
    text = vacancy_page.job_text
    if not text:
        raise HTTPException(
            status_code=502, detail="Не удалось распарсить вакансию по URL"
        )

    job_parse = JobParsePrompt()
    chain = job_parse.prompt_template | job_parse.get_model
    vacancy: JobRequirement = chain.invoke({"job_text": text})

    ranked = await projects_service.rank_projects_overlap(
        user_id=user.id,
        vacancy=vacancy,
        top_k=5,
    )

    return {
        "result": vacancy,
        "body": body.url,
        "ranked_projects": ranked,
    }
