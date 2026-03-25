# models/cv.py
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel


class CV(SQLModel, table=True):
    """CV/Resume model"""
    __tablename__ = "cvs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    source_id: str = Field(unique=True, nullable=False, index=True)
    filename: str = Field(nullable=False, max_length=255)
    original_filename: str = Field(nullable=False, max_length=255)
    file_path: Optional[str] = Field(default=None, max_length=500)
    file_size: int = Field(nullable=False)
    content_type: str = Field(nullable=False, max_length=100)
    status: str = Field(default="uploaded", max_length=50)  # uploaded, processed, error

    # Metadata
    upload_ip: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="cvs")
    letters: List["Letter"] = Relationship(
        back_populates="cv", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def __repr__(self):
        return f"<CV(id={self.id}, user_id={self.user_id}, source_id={self.source_id}, filename={self.filename})>"