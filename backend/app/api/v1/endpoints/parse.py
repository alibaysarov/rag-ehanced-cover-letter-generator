import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.cache import redis as redis_db
from app.helper.user import CurrentUser
from app.schemas.llm_outputs.job_requirements import JobRequirement
from app.services.llm.agents.tools.fetch_url import parse_hh
from app.services.llm.job_requirements import JobParsePrompt
from app.dependencies import get_projects_storage_service
from app.services.projects import ProjectStorageService

logger = logging.getLogger(__name__)
router = APIRouter()


class ParseDto(BaseModel):
    url: str




@router.post("")
async def parse(
    user:CurrentUser,
    body: ParseDto,
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    
    cached = await redis_db.redis_client.get(body.url)
    if cached is None:
        text = await parse_hh(body.url)
        if not text:
            raise HTTPException(status_code=502, detail="Не удалось распарсить вакансию по URL")
        await redis_db.redis_client.set(body.url, text, ex=3600)
    else:
        text = cached

    job_parse = JobParsePrompt()
    chain = job_parse.prompt_template | job_parse.get_model
    vacancy: JobRequirement = chain.invoke({"job_text": text})

    ranked = projects_service.rank_projects_overlap(
        user_id=user.id,
        vacancy=vacancy,
        top_k=5,
    )

    return {
        "result": vacancy,
        "body": body.url,
        "ranked_projects": ranked,
    }
