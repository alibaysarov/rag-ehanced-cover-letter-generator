from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class ParsingJob(SQLModel, table=True):
    __tablename__ = "parsing_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    query: str = Field(nullable=False)
    status: str = Field(default="pending")  # pending | running | done | failed
    total_found: int = Field(default=0)
    saved_count: int = Field(default=0)
    error: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None, nullable=True)
