from typing import Optional

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
    website: Optional[str] = None
    start_month: Optional[int] = None
    start_year: Optional[int] = None
    end_month: Optional[int] = None
    end_year: Optional[int] = None
    currently_working: bool = False
    skills: list[str] = []
    achievements: list[str] = []
    technologies: list[str] = []


class ListProjectsResponse(BaseModel):
    projects: list[ProjectResponse]


class UpdateProjectRequest(BaseModel):
    name: str
    website: Optional[str] = None
    start_month: Optional[int] = None
    start_year: Optional[int] = None
    end_month: Optional[int] = None
    end_year: Optional[int] = None
    currently_working: bool = False
    skills: list[str] = []
    achievements: list[str] = []
    technologies: list[str] = []
