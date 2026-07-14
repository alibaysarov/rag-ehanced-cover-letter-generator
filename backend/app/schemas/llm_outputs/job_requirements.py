from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str = Field("Название навыка")


class JobRequirement(BaseModel):
    name: str = Field(...,description="Название вакансии")
    lang: str = Field(..., description="язык на котором написана вакансия (прим. RU,EN)")
    project_name: str = Field("Название/область проекта")
    required_technologies: list[str] = Field(
        default_factory=list,
        description="Обязательные технологии (must-have, явно требуются в вакансии).",
    )
    preferred_technologies: list[str] = Field(
        default_factory=list,
        description="Желательные технологии",
    )
    nice_to_have_technologies: list[str] = Field(
        default_factory=list,
        description="Опциональные/nice-to-have технологии",
    )
    requirements: list[str] = Field(default_factory=list, description="Требуемые навыки и компетенции")

    @property
    def technologies(self) -> list[str]:
        return (
            self.required_technologies
            + self.preferred_technologies
            + self.nice_to_have_technologies
        )
