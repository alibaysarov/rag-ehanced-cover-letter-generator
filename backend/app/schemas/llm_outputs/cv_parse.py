from pydantic import BaseModel, Field
from typing import Optional


class ProjectFromCVModel(BaseModel):
    name: str = Field(
        ...,
        description="Название компании или проекта (например, 'AMAZON,Oracle,Microsoft)"
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Профессиональные навыки и компетенции, применённые в проекте (например, 'REST API design', 'геопространственная индексация', 'оптимизация производительности'). НЕ включай сюда конкретные технологии."
    )
    achievements: list[str] = Field(
        default_factory=list,
        description="Действия, и конкретные достижения и результаты, желательно с метриками"
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Только названия технологий, языков, фреймворков, баз данных, инструментов (например, 'Node.js', 'PostgreSQL', 'Docker'). Одна технология на пункт"
    )


class CVImportModel(BaseModel):
    first_name: str = Field(
        ...,
        description="Имя кандидата, извлечённое из резюме (только имя, без фамилии)"
    )
    last_name: str = Field(
        ...,
        description="Фамилия кандидата, извлечённая из резюме (только фамилия, без имени)"
    )
    email: Optional[str] = Field(
        None,
        description="Email кандидата, если указан в резюме. Если email не найден — null."
    )
    projects: list[ProjectFromCVModel] = Field(
        default_factory=list,
        description="Список мест работы или проектов кандидата"
    )