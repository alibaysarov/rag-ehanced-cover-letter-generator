from pydantic import BaseModel, Field


class Skill(BaseModel):
    name:str = Field("Название навыка")
    

class JobRequirement(BaseModel):
    name: str = Field("Название вакансии")
    lang:str = Field(...,description="язык на котором написана вакансия (прим. RU,EN)")
    project_name: str = Field("Название/область проекта")
    requirements: list[str] = Field("Требуемые навыки и компетенции")
