from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    """User model for authentication"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, nullable=False, index=True, max_length=255)
    password_hash: str = Field(nullable=False, max_length=255)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)

    # Profile information
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    cvs: List["CV"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"