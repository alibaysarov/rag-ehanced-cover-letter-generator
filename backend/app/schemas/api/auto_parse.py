from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.generation_mode import GenerationMode


class AutoParseResponse(BaseModel):
    total: int
    generated: int


class StartParseRequest(BaseModel):
    query: str
    generation_mode: GenerationMode = GenerationMode.AI
    vacancy_limit: int | None = Field(default=None, ge=1, le=1000, strict=True)


class MarkAppliedRequest(BaseModel):
    letter_text: str = ""


class AutoParsedJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parsing_job_id: int | None
    vacancy_id: str | None
    url: str
    web_site: str | None
    job_title: str
    job_text: str
    company_name: str | None
    is_applied: bool
    is_viewed: bool
    is_generated: bool
    cover_letter_text: str | None
    created_at: datetime


class ParsingVacancySavedEvent(BaseModel):
    type: str = "parsing.vacancy_saved"
    user_id: int
    parsing_job_id: int
    site_key: str
    vacancy: AutoParsedJobRead


class TemplateVacancyReadyEvent(BaseModel):
    type: Literal["generation.vacancy_ready"] = "generation.vacancy_ready"
    user_id: int
    batch_id: str | int
    parsing_job_id: int
    status: Literal["generated"] = "generated"
    generation_mode: Literal["template"] = "template"
    vacancy: AutoParsedJobRead
