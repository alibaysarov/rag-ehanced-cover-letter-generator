"""create_letters_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-06 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create letters table."""
    op.create_table(
        'letters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('cv_id', sa.Integer(), sa.ForeignKey('cvs.id'), nullable=False, index=True),
        sa.Column('source_id', sa.Integer(), nullable=False, index=True),
        sa.Column('job_title', sa.String(length=200), nullable=False),
        sa.Column('job_description', sa.Text(), nullable=True),
        sa.Column('company_name', sa.String(length=200), nullable=True),
        sa.Column('job_url', sa.String(length=500), nullable=True),
        sa.Column('letter_content', sa.Text(), nullable=False),
        sa.Column('job_requirements', sa.Text(), nullable=True),
        sa.Column('generation_time', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=False, server_default='gpt-4o'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='generated'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop letters table."""
    op.drop_table('letters')
