from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel


class JobSite(SQLModel, table=True):
    """Job site for multiple parsers"""
    __tablename__ = "job_sites"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    base_url: str = Field(unique=True, nullable=False, index=True, max_length=255)
    vacancy_url: str= Field(nullable=False, index=True, max_length=255)