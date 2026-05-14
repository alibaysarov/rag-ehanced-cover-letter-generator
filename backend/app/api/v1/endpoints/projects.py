import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dto.projects import (
    ListProjectsResponse,
    ProjectResponse,
    SaveProjectsRequest,
    SaveProjectsResponse,
    UpdateProjectRequest,
)
from app.helper.user import get_user_repository
from app.repository.user_repository import UserRepository
from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel
from app.services.projects import ProjectStorageService, get_projects_service

logger = logging.getLogger(__name__)
router = APIRouter()


def get_projects_storage_service() -> ProjectStorageService:
    return get_projects_service()


def _get_current_user(request: Request, user_repo: UserRepository):
    user_email = request.state.user_email
    user = user_repo.get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/save", response_model=SaveProjectsResponse)
async def save_projects(
    body: SaveProjectsRequest,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    user = _get_current_user(request, user_repo)
    saved = projects_service.save_projects(
        user_id=user.id,
        source_id=body.source_id,
        projects=body.projects,
    )
    return SaveProjectsResponse(saved=saved)


@router.get("/", response_model=ListProjectsResponse)
async def list_projects(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    user = _get_current_user(request, user_repo)
    projects = projects_service.list_user_projects(user_id=user.id)
    return ListProjectsResponse(projects=[ProjectResponse(**p) for p in projects])


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    user = _get_current_user(request, user_repo)
    project_model = ProjectFromCVModel(
        name=body.name,
        skills=body.skills,
        achievements=body.achievements,
        technologies=body.technologies,
    )
    try:
        updated = projects_service.update_project(
            user_id=user.id,
            project_id=project_id,
            project=project_model,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(**updated)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    user = _get_current_user(request, user_repo)
    try:
        projects_service.delete_project(user_id=user.id, project_id=project_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "success": True,
        "message": f"Project {project_id} deleted successfully",
    }
