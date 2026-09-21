from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Column, String, Text
from sqlmodel import Field, SQLModel

from app.schemas.generation_mode import GenerationMode


class ParsingJob(SQLModel, table=True):
    __tablename__ = "parsing_jobs"
    __table_args__ = (
        CheckConstraint(
            "generation_mode IN ('ai', 'template')",
            name="ck_parsing_jobs_generation_mode",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    query: str = Field(nullable=False)
    status: str = Field(default="pending")  # pending | running | done | failed
    total_found: int = Field(default=0)
    saved_count: int = Field(default=0)
    error: Optional[str] = Field(default=None, nullable=True)
    generation_mode: GenerationMode = Field(
        default=GenerationMode.AI,
        sa_column=Column(
            String, nullable=False, server_default=GenerationMode.AI.value
        ),
    )
    auto_generation_started_at: Optional[datetime] = Field(default=None, nullable=True)
    auto_generation_error: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None, nullable=True)
