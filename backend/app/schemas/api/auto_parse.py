from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AutoParseResponse(BaseModel):
    total: int
    generated: int


class StartParseRequest(BaseModel):
    query: str


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
