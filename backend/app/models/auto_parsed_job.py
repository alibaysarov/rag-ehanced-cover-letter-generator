from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class AutoParsedJob(SQLModel, table=True):
    __tablename__ = "auto_parsed_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    parsing_job_id: int = Field(foreign_key="parsing_jobs.id", index=True, nullable=False)
    vacancy_id: str = Field(nullable=False)
    url: str = Field(nullable=False)
    job_title: str = Field(nullable=False)
    job_text: str = Field(nullable=False)
    is_applied: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
