"""add cover letter template graph

Revision ID: o2d3e4f5a6b7
Revises: n1c2d3e4f5a6
Create Date: 2026-09-21 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "o2d3e4f5a6b7"
down_revision = "n1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("defaults_provisioned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "letter_phrases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('opening', 'experience_bridge', 'portfolio_intro', "
            "'stack_summary', 'closing', 'custom')",
            name="ck_letter_phrases_type",
        ),
        sa.CheckConstraint(
            "char_length(btrim(text)) BETWEEN 1 AND 2000",
            name="ck_letter_phrases_text_length",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_letter_phrases_user_id", "letter_phrases", ["user_id"])
    op.create_index(
        "ix_letter_phrases_user_type_active",
        "letter_phrases",
        ["user_id", "type", "is_active"],
    )

    op.create_table(
        "cover_letter_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("template_case", sa.String(length=40), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="draft", nullable=False
        ),
        sa.Column("root_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "template_case IN ('no_portfolio', 'relevant_domain', 'partial_match', "
            "'no_relevant_projects')",
            name="ck_cover_letter_templates_case",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_cover_letter_templates_status",
        ),
        sa.CheckConstraint(
            "status <> 'active' OR root_node_id IS NOT NULL",
            name="ck_cover_letter_templates_active_root",
        ),
        sa.CheckConstraint("version >= 1", name="ck_cover_letter_templates_version"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cover_letter_templates_user_id", "cover_letter_templates", ["user_id"]
    )
    op.create_index(
        "uq_cover_letter_templates_active_case",
        "cover_letter_templates",
        ["user_id", "template_case"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "cover_letter_template_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("node_kind", sa.String(length=20), nullable=False),
        sa.Column("phrase_id", sa.BigInteger(), nullable=True),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "node_kind IN ('phrase', 'projects')",
            name="ck_cover_letter_template_nodes_kind",
        ),
        sa.CheckConstraint(
            "(node_kind = 'phrase' AND phrase_id IS NOT NULL) OR "
            "(node_kind = 'projects' AND phrase_id IS NULL)",
            name="ck_cover_letter_template_nodes_kind_phrase",
        ),
        sa.ForeignKeyConstraint(
            ["phrase_id"], ["letter_phrases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["cover_letter_templates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id", "id", name="uq_template_nodes_template_id_id"
        ),
    )
    op.create_index(
        "ix_cover_letter_template_nodes_template_id",
        "cover_letter_template_nodes",
        ["template_id"],
    )
    op.create_index(
        "ix_cover_letter_template_nodes_phrase_id",
        "cover_letter_template_nodes",
        ["phrase_id"],
    )
    op.create_index(
        "uq_cover_letter_template_nodes_projects",
        "cover_letter_template_nodes",
        ["template_id"],
        unique=True,
        postgresql_where=sa.text("node_kind = 'projects'"),
    )
    op.create_foreign_key(
        "fk_cover_letter_templates_root_node_id",
        "cover_letter_templates",
        "cover_letter_template_nodes",
        ["root_node_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "cover_letter_template_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "source_node_id <> target_node_id", name="ck_template_edges_no_self_loop"
        ),
        sa.CheckConstraint(
            "branch_order >= 0", name="ck_template_edges_branch_order"
        ),
        sa.ForeignKeyConstraint(
            ["template_id", "source_node_id"],
            ["cover_letter_template_nodes.template_id", "cover_letter_template_nodes.id"],
            name="fk_template_edges_source",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id", "target_node_id"],
            ["cover_letter_template_nodes.template_id", "cover_letter_template_nodes.id"],
            name="fk_template_edges_target",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_node_id", "branch_order", name="uq_template_edges_branch_order"
        ),
        sa.UniqueConstraint(
            "template_id",
            "source_node_id",
            "target_node_id",
            name="uq_template_edges_source_target",
        ),
    )
    op.create_index(
        "ix_cover_letter_template_edges_template_id",
        "cover_letter_template_edges",
        ["template_id"],
    )

    op.add_column(
        "auto_parsed_jobs", sa.Column("company_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "auto_parsed_jobs",
        sa.Column("cover_letter_template_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "auto_parsed_jobs",
        sa.Column("cover_letter_template_case", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "auto_parsed_jobs",
        sa.Column("cover_letter_template_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "auto_parsed_jobs",
        sa.Column("cover_letter_template_path", postgresql.JSONB(), nullable=True),
    )
    op.create_foreign_key(
        "fk_auto_parsed_jobs_cover_letter_template_id",
        "auto_parsed_jobs",
        "cover_letter_templates",
        ["cover_letter_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_auto_parsed_jobs_template_case",
        "auto_parsed_jobs",
        "cover_letter_template_case IS NULL OR cover_letter_template_case IN "
        "('no_portfolio', 'relevant_domain', 'partial_match', 'no_relevant_projects')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_auto_parsed_jobs_template_case", "auto_parsed_jobs", type_="check"
    )
    op.drop_constraint(
        "fk_auto_parsed_jobs_cover_letter_template_id",
        "auto_parsed_jobs",
        type_="foreignkey",
    )
    op.drop_column("auto_parsed_jobs", "cover_letter_template_path")
    op.drop_column("auto_parsed_jobs", "cover_letter_template_version")
    op.drop_column("auto_parsed_jobs", "cover_letter_template_case")
    op.drop_column("auto_parsed_jobs", "cover_letter_template_id")
    op.drop_column("auto_parsed_jobs", "company_name")

    op.drop_table("cover_letter_template_edges")
    op.drop_constraint(
        "fk_cover_letter_templates_root_node_id",
        "cover_letter_templates",
        type_="foreignkey",
    )
    op.drop_table("cover_letter_template_nodes")
    op.drop_table("cover_letter_templates")
    op.drop_table("letter_phrases")
    op.drop_column("users", "defaults_provisioned_at")
