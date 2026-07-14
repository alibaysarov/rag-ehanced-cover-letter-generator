from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel,Column
from sqlalchemy.dialects.postgresql import ARRAY
from typing import Optional, List
from sqlalchemy import String,Index


class Project(SQLModel,table=True):
    __tablename__ = "projects"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    name:str = Field(nullable=False)
    web_site:str = Field(nullable=True)
    company_name:str = Field(nullable=False)
    
    technologies: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String))
    )
    
    skills: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String),nullable=True),
    )
    
    achievements: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String),nullable=True),
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(back_populates="projects")
    
    __table_args__ = (
        Index(
            "ix_projects_technologies_gin",
            "technologies",
            postgresql_using="gin",
        ),
    )