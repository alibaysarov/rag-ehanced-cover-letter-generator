from pydantic import BaseModel

from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel


class SaveProjectsRequest(BaseModel):
    source_id: str
    projects: list[ProjectFromCVModel]


class SaveProjectsResponse(BaseModel):
    saved: int


class ProjectResponse(BaseModel):
    id: str
    source_id: str
    name: str
    skills: list[str] = []
    achievements: list[str] = []
    technologies: list[str] = []


class ListProjectsResponse(BaseModel):
    projects: list[ProjectResponse]


class UpdateProjectRequest(BaseModel):
    name: str
    skills: list[str] = []
    achievements: list[str] = []
    technologies: list[str] = []
