from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str = Field("Название навыка")


class JobRequirement(BaseModel):
    name: str = Field(...,description="Название вакансии")
    lang: str = Field(..., description="язык на котором написана вакансия (прим. RU,EN)")
    project_name: str = Field("Название/область проекта")
    required_technologies: list[str] = Field(
        default_factory=list,
        description="Обязательные технологии (must-have, явно требуются в вакансии). Все в нижнем регистре.",
    )
    preferred_technologies: list[str] = Field(
        default_factory=list,
        description="Желательные технологии ('будет плюсом', 'опыт с', 'приветствуется'). Все в нижнем регистре.",
    )
    nice_to_have_technologies: list[str] = Field(
        default_factory=list,
        description="Опциональные/nice-to-have технологии ('знакомство с', 'понимание основ'). Все в нижнем регистре.",
    )
    requirements: list[str] = Field(default_factory=list, description="Требуемые навыки и компетенции")

    @property
    def technologies(self) -> list[str]:
        return (
            self.required_technologies
            + self.preferred_technologies
            + self.nice_to_have_technologies
        )
