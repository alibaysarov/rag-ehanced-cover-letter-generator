import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.helper.user import get_user_repository
from app.repository.user_repository import UserRepository
from app.schemas.llm_outputs.job_requirements import JobRequirement
from app.services.llm.agents.tools.fetch_url import parse_hh
from app.services.llm.job_requirements import JobParsePrompt
from app.services.projects import ProjectStorageService, get_projects_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ParseDto(BaseModel):
    url: str


def get_projects_storage_service() -> ProjectStorageService:
    return get_projects_service()


@router.post("")
async def parse(
    body: ParseDto,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    user_email = request.state.user_email
    user = user_repo.get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    text = await parse_hh(body.url)

    job_parse = JobParsePrompt()
    chain = job_parse.prompt_template | job_parse.get_model
    vacancy: JobRequirement = chain.invoke({"job_text": text})

    ranked = projects_service.rank_projects(
        user_id=user.id,
        vacancy=vacancy,
        top_k=5,
    )

    return {
        "result": vacancy,
        "body": body.url,
        "ranked_projects": ranked,
    }
