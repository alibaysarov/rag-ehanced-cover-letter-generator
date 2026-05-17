"""add_generation_time_ms_to_sent_letters

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sent_cover_letters',
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('sent_cover_letters', 'generation_time_ms')
