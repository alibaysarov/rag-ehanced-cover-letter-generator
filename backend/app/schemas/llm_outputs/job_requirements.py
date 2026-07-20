from pydantic import BaseModel, Field, model_validator


class Skill(BaseModel):
    name: str = Field("Название навыка")


class JobRequirement(BaseModel):
    id: int | str = Field(..., description="id вакансии")
    name: str = Field(..., description="Название вакансии")
    technologies: list[str] = Field(
        default_factory=list,
        description="Список технологий",
    )

    @model_validator(mode="before")
    @classmethod
    def fill_missing_name(cls, data):
        if isinstance(data, dict) and not data.get("name"):
            data["name"] = "Без названия"
        return data
