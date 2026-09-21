from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    company_name: str | None = Field(default=None, max_length=255)
    is_applied: bool = Field(default=False)
    is_viewed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_generated: bool = Field(default=False)
    cover_letter_text: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    cover_letter_template_id: int | None = Field(
        default=None,
        # The FK is installed by Alembic. Keeping it out of this isolated table
        # metadata lets repository tests create AutoParsedJob without creating
        # the entire circular template graph first.
        sa_column=Column(BigInteger, nullable=True),
    )
    cover_letter_template_case: str | None = Field(
        default=None, sa_column=Column(String(40), nullable=True)
    )
    cover_letter_template_version: int | None = Field(default=None)
    cover_letter_template_path: list[str] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
