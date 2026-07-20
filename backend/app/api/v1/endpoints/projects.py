import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.dto.projects import (
    ListProjectsResponse,
    ProjectResponse,
    SaveProjectsRequest,
    SaveProjectsResponse,
    UpdateProjectRequest,
)
from app.helper.user import CurrentUser
from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel
from app.dependencies import get_projects_storage_service
from app.services.projects import ProjectStorageService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/save", response_model=SaveProjectsResponse)
async def save_projects(
    user:CurrentUser,
    body: SaveProjectsRequest,
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    saved = await projects_service.create_many(
        user_id=user.id,
        projects=body.projects,
    )
    return SaveProjectsResponse(saved=saved)


@router.get("/", response_model=ListProjectsResponse)
async def list_projects(
    user:CurrentUser,
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    
    projects = projects_service.list_user_projects(user_id=user.id)
    return ListProjectsResponse(projects=[ProjectResponse(**p) for p in projects])


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    user:CurrentUser,
    project_id: str,
    body: UpdateProjectRequest,
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
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
    user:CurrentUser,
    project_id: str,
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    try:
        projects_service.delete_project(user_id=user.id, project_id=project_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "success": True,
        "message": f"Project {project_id} deleted successfully",
    }
