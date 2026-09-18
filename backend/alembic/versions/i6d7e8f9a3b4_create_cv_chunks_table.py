"""create_cv_chunks_table

Revision ID: i6d7e8f9a3b4
Revises: h5c6d7e8f9a2
Create Date: 2026-09-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "i6d7e8f9a3b4"
down_revision: Union[str, Sequence[str], None] = "h5c6d7e8f9a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cv_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_cv_chunks_user_id", "cv_chunks", ["user_id"])
    op.create_index("ix_cv_chunks_source_id", "cv_chunks", ["source_id"])
    op.create_index(
        "ix_cv_chunks_source_chunk",
        "cv_chunks",
        ["source_id", "chunk_index"],
        unique=True,
    )
    op.execute(
        "CREATE INDEX ix_cv_chunks_text_tsv "
        "ON cv_chunks USING gin (to_tsvector('simple', text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cv_chunks_text_tsv")
    op.drop_index("ix_cv_chunks_source_chunk", table_name="cv_chunks")
    op.drop_index("ix_cv_chunks_source_id", table_name="cv_chunks")
    op.drop_index("ix_cv_chunks_user_id", table_name="cv_chunks")
    op.drop_table("cv_chunks")
