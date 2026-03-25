# models/letter.py
from datetime import datetime
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel


class Letter(SQLModel, table=True):
    """Generated cover letter model"""
    __tablename__ = "letters"

    id: Optional[int] = Field(default=None, primary_key=True)
    cv_id: int = Field(foreign_key="cvs.id", nullable=False, index=True)
    source_id: int = Field(nullable=False, index=True)  # Redundant for faster queries

    # Job information
    job_title: str = Field(nullable=False, max_length=200)
    job_description: Optional[str] = Field(default=None)
    company_name: Optional[str] = Field(default=None, max_length=200)
    job_url: Optional[str] = Field(default=None, max_length=500)

    # Generated content
    letter_content: str = Field(nullable=False)
    job_requirements: Optional[str] = Field(default=None)  # Extracted/analyzed requirements

    # Generation metadata
    generation_time: Optional[int] = Field(default=None)  # Time in seconds
    model_used: str = Field(default="gpt-4o", max_length=100)
    status: str = Field(default="generated", max_length=50)  # generated, error

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    cv: Optional["CV"] = Relationship(back_populates="letters")

    def __repr__(self):
        title_preview = self.job_title[:30] if len(self.job_title) > 30 else self.job_title
        return f"<Letter(id={self.id}, cv_id={self.cv_id}, job_title={title_preview}...)>"