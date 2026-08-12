from pydantic import BaseModel


class RelevantProjectResponse(BaseModel):
    id: int
    name: str
    project_name: str
    technologies: list[str]
