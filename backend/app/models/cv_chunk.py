from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CVChunk(SQLModel, table=True):
    __tablename__ = "cv_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    source_id: str = Field(nullable=False, index=True)
    chunk_index: int = Field(nullable=False)
    text: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
