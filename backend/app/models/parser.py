from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Parser(SQLModel, table=True):
    __tablename__ = "parsers"
    __table_args__ = (
        UniqueConstraint("user_id", "site_key", name="uq_parsers_user_site_key"),
        Index("ix_parsers_user_created_id", "user_id", "created_at", "id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", nullable=False, index=True)
    name: str = Field(max_length=255, nullable=False)
    site_key: str = Field(max_length=255, nullable=False)
    base_url: str = Field(sa_column=Column(Text, nullable=False))
    single_url: str = Field(sa_column=Column(Text, nullable=False))
    has_pagination: bool = Field(nullable=False)
    evaluate_vacancy_list: str = Field(sa_column=Column(Text, nullable=False))
    evaluate_vacancy_page: str = Field(sa_column=Column(Text, nullable=False))
    evaluate_pagination: str | None = Field(default=None, sa_column=Column(Text))
    format_url: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    pagination_start: int = Field(default=0, nullable=False)
    max_pages: int = Field(default=5, nullable=False)
    version: int = Field(default=1, nullable=False)
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )


class ParserUsage(SQLModel, table=True):
    __tablename__ = "parser_usages"
    __table_args__ = (
        Index("ix_parser_usages_parser_expires", "parser_id", "expires_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    parser_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("parsers.id", ondelete="CASCADE"), nullable=False
        )
    )
    user_id: int = Field(foreign_key="users.id", nullable=False)
    started_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    expires_at: datetime = Field(nullable=False)
