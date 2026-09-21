from datetime import datetime
from typing import Any

from sqlalchemy import Column, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ParsingSiteJob(SQLModel, table=True):
    __tablename__ = "parsing_site_jobs"
    __table_args__ = (
        UniqueConstraint(
            "parsing_job_id", "site_key", name="uq_parsing_site_jobs_job_site"
        ),
        Index("ix_parsing_site_jobs_parser_status", "parser_id", "status"),
    )

    id: int | None = Field(default=None, primary_key=True)
    parsing_job_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("parsing_jobs.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
    )
    site_key: str = Field(nullable=False)
    parser_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("parsers.id", ondelete="SET NULL"), nullable=True
        ),
    )
    parser_version: int | None = Field(default=None, nullable=True)
    vacancy_limit: int | None = Field(default=None, nullable=True, ge=1)
    parser_snapshot: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    status: str = Field(default="pending", nullable=False)
    total_found: int = Field(default=0, nullable=False)
    saved_count: int = Field(default=0, nullable=False)
    failed_count: int = Field(default=0, nullable=False)
    error: str | None = Field(default=None, sa_type=Text, nullable=True)
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
