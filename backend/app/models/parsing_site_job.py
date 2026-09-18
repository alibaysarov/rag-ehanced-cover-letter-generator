from datetime import datetime

from sqlalchemy import Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class ParsingSiteJob(SQLModel, table=True):
    __tablename__ = "parsing_site_jobs"
    __table_args__ = (
        UniqueConstraint(
            "parsing_job_id", "site_key", name="uq_parsing_site_jobs_job_site"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    parsing_job_id: int = Field(
        foreign_key="parsing_jobs.id", index=True, nullable=False
    )
    site_key: str = Field(nullable=False)
    status: str = Field(default="pending", nullable=False)
    total_found: int = Field(default=0, nullable=False)
    saved_count: int = Field(default=0, nullable=False)
    failed_count: int = Field(default=0, nullable=False)
    error: str | None = Field(default=None, sa_type=Text, nullable=True)
    started_at: datetime | None = Field(default=None, nullable=True)
    finished_at: datetime | None = Field(default=None, nullable=True)
