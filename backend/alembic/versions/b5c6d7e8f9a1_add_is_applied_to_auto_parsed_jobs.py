"""add_is_applied_to_auto_parsed_jobs

Revision ID: b5c6d7e8f9a1
Revises: a4b5c6d7e8f9
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = 'b5c6d7e8f9a1'
down_revision: Union[str, Sequence[str], None] = 'a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('auto_parsed_jobs')]
    if 'is_applied' not in columns:
        op.add_column(
            'auto_parsed_jobs',
            sa.Column('is_applied', sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column('auto_parsed_jobs', 'is_applied')
