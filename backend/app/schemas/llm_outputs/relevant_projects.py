from pydantic import BaseModel,Field


class RelevantProject(BaseModel):
    id: int|str = Field(...,description="ID проекта")
    # name: str = Field(...,description="Название проекта")
    # technologies:list[str] = Field(...,description="Список технологий")
    count: int

class RelevantProjects(BaseModel):
    projects:list[RelevantProject] = Field(...,description="Список подходящих проектов")
    
