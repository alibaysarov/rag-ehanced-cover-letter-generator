"""add per-site vacancy limits

Revision ID: n1c2d3e4f5a6
Revises: m0b1c2d3e4f5
"""

import sqlalchemy as sa
from alembic import op

revision = "n1c2d3e4f5a6"
down_revision = "m0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parsing_site_jobs", sa.Column("vacancy_limit", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("parsing_site_jobs", "vacancy_limit")
