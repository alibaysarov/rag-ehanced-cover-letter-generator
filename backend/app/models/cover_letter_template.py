from datetime import datetime, timezone
from typing import ClassVar, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from app.domain.template_enums import (
    LetterPhraseType,
    TemplateCase,
    TemplateNodeKind,
    TemplateStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LetterPhrase(SQLModel, table=True):
    __tablename__: ClassVar[str] = "letter_phrases"
    __table_args__ = (
        CheckConstraint(
            "type IN ('opening', 'experience_bridge', 'portfolio_intro', "
            "'stack_summary', 'closing', 'custom')",
            name="ck_letter_phrases_type",
        ),
        CheckConstraint(
            "char_length(btrim(text)) BETWEEN 1 AND 2000",
            name="ck_letter_phrases_text_length",
        ),
        Index("ix_letter_phrases_user_type_active", "user_id", "type", "is_active"),
    )

    id: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    type: LetterPhraseType = Field(sa_column=Column(String(40), nullable=False))
    text: str = Field(sa_column=Column(Text, nullable=False))
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CoverLetterTemplate(SQLModel, table=True):
    __tablename__: ClassVar[str] = "cover_letter_templates"
    __table_args__ = (
        CheckConstraint(
            "template_case IN ('no_portfolio', 'relevant_domain', 'partial_match', "
            "'no_relevant_projects')",
            name="ck_cover_letter_templates_case",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_cover_letter_templates_status",
        ),
        CheckConstraint(
            "status <> 'active' OR root_node_id IS NOT NULL",
            name="ck_cover_letter_templates_active_root",
        ),
        CheckConstraint("version >= 1", name="ck_cover_letter_templates_version"),
        Index(
            "uq_cover_letter_templates_active_case",
            "user_id",
            "template_case",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Optional[int] = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: str = Field(sa_column=Column(String(120), nullable=False))
    template_case: TemplateCase = Field(sa_column=Column(String(40), nullable=False))
    status: TemplateStatus = Field(
        default=TemplateStatus.DRAFT,
        sa_column=Column(String(20), nullable=False, server_default="draft"),
    )
    root_node_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey(
                "cover_letter_template_nodes.id",
                name="fk_cover_letter_templates_root_node_id",
                use_alter=True,
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )
    version: int = Field(
        default=1, sa_column=Column(Integer, nullable=False, server_default="1")
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CoverLetterTemplateNode(SQLModel, table=True):
    __tablename__: ClassVar[str] = "cover_letter_template_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_kind IN ('phrase', 'projects')",
            name="ck_cover_letter_template_nodes_kind",
        ),
        CheckConstraint(
            "(node_kind = 'phrase' AND phrase_id IS NOT NULL) OR "
            "(node_kind = 'projects' AND phrase_id IS NULL)",
            name="ck_cover_letter_template_nodes_kind_phrase",
        ),
        UniqueConstraint("template_id", "id", name="uq_template_nodes_template_id_id"),
        Index(
            "uq_cover_letter_template_nodes_projects",
            "template_id",
            unique=True,
            postgresql_where=text("node_kind = 'projects'"),
        ),
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True),
    )
    template_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey("cover_letter_templates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    node_kind: TemplateNodeKind = Field(sa_column=Column(String(20), nullable=False))
    phrase_id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            ForeignKey("letter_phrases.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
    )
    position_x: float = Field(sa_column=Column(Float, nullable=False))
    position_y: float = Field(sa_column=Column(Float, nullable=False))


class CoverLetterTemplateEdge(SQLModel, table=True):
    __tablename__: ClassVar[str] = "cover_letter_template_edges"
    __table_args__ = (
        CheckConstraint(
            "source_node_id <> target_node_id", name="ck_template_edges_no_self_loop"
        ),
        CheckConstraint("branch_order >= 0", name="ck_template_edges_branch_order"),
        UniqueConstraint(
            "template_id",
            "source_node_id",
            "target_node_id",
            name="uq_template_edges_source_target",
        ),
        UniqueConstraint(
            "source_node_id", "branch_order", name="uq_template_edges_branch_order"
        ),
        ForeignKeyConstraint(
            ["template_id", "source_node_id"],
            [
                "cover_letter_template_nodes.template_id",
                "cover_letter_template_nodes.id",
            ],
            name="fk_template_edges_source",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["template_id", "target_node_id"],
            [
                "cover_letter_template_nodes.template_id",
                "cover_letter_template_nodes.id",
            ],
            name="fk_template_edges_target",
            ondelete="CASCADE",
        ),
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True),
    )
    template_id: int = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    source_node_id: UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False))
    target_node_id: UUID = Field(sa_column=Column(PGUUID(as_uuid=True), nullable=False))
    branch_order: int = Field(sa_column=Column(Integer, nullable=False))
