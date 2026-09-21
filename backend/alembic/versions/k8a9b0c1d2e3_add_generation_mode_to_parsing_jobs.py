"""add generation mode to parsing jobs

Revision ID: k8a9b0c1d2e3
Revises: k8f9a0b1c5d6
"""
import sqlalchemy as sa
from alembic import op

revision = "k8a9b0c1d2e3"
down_revision = "k8f9a0b1c5d6"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("parsing_jobs", sa.Column("generation_mode", sa.String(), nullable=False, server_default="ai"))
    op.add_column("parsing_jobs", sa.Column("auto_generation_started_at", sa.DateTime(), nullable=True))
    op.add_column("parsing_jobs", sa.Column("auto_generation_error", sa.Text(), nullable=True))
    op.create_check_constraint("ck_parsing_jobs_generation_mode", "parsing_jobs", "generation_mode IN ('ai', 'template')")

def downgrade() -> None:
    op.drop_constraint("ck_parsing_jobs_generation_mode", "parsing_jobs", type_="check")
    op.drop_column("parsing_jobs", "auto_generation_error")
    op.drop_column("parsing_jobs", "auto_generation_started_at")
    op.drop_column("parsing_jobs", "generation_mode")
