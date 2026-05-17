from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class SentCoverLetter(SQLModel, table=True):
    __tablename__ = "sent_cover_letters"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    url: Optional[str] = Field(default=None)
    job_name: Optional[str] = Field(default=None)
    type: str = Field(default="other")  # "hh.ru" | "linkedin" | "other"
    letter_text: str = Field(nullable=False)
    is_accepted: bool = Field(default=False)
    generation_time_ms: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
