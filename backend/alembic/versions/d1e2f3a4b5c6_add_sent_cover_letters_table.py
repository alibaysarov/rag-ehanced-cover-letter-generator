"""add_sent_cover_letters_table

Revision ID: d1e2f3a4b5c6
Revises: 992d76276b2f
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = '992d76276b2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sent_cover_letters table."""
    op.create_table(
        'sent_cover_letters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('job_name', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='other'),
        sa.Column('letter_text', sa.Text(), nullable=False),
        sa.Column('is_accepted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_sent_cover_letters_user_id', 'sent_cover_letters', ['user_id'])


def downgrade() -> None:
    """Drop sent_cover_letters table."""
    op.drop_index('ix_sent_cover_letters_user_id', table_name='sent_cover_letters')
    op.drop_table('sent_cover_letters')
