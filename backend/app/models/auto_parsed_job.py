from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class AutoParsedJob(SQLModel, table=True):
    __tablename__ = "auto_parsed_jobs"
    __table_args__ = (
        UniqueConstraint(
            "parsing_site_job_id",
            "vacancy_id",
            name="uq_auto_parsed_jobs_site_vacancy",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    parsing_job_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("parsing_jobs.id", ondelete="CASCADE"),
            index=True,
            nullable=True,
        ),
    )
    parsing_site_job_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("parsing_site_jobs.id", ondelete="CASCADE"),
            index=True,
            nullable=True,
        ),
    )
    vacancy_id: str = Field(nullable=True)
    url: str = Field(nullable=False)
    job_title: str = Field(nullable=False)
    job_text: str = Field(nullable=False)
    web_site: str = Field(nullable=True)
    is_applied: bool = Field(default=False)
    is_viewed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_generated: bool = Field(default=False)
    cover_letter_text: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
