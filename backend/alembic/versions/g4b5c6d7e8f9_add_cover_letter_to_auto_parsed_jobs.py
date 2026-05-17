"""add_cover_letter_to_auto_parsed_jobs

Revision ID: g4b5c6d7e8f9
Revises: b5c6d7e8f9a1
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = 'g4b5c6d7e8f9'
down_revision: Union[str, Sequence[str], None] = 'b5c6d7e8f9a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # Ensure the auto_parsed_jobs table exists (may have been created via create_all, not migration)
    if not inspector.has_table('auto_parsed_jobs'):
        op.create_table(
            'auto_parsed_jobs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('parsing_job_id', sa.Integer(), nullable=False),
            sa.Column('vacancy_id', sa.Text(), nullable=False),
            sa.Column('url', sa.Text(), nullable=False),
            sa.Column('job_title', sa.Text(), nullable=False),
            sa.Column('job_text', sa.Text(), nullable=False),
            sa.Column('is_applied', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('is_generated', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('cover_letter_text', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['parsing_job_id'], ['parsing_jobs.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_auto_parsed_jobs_user_id'), 'auto_parsed_jobs', ['user_id'], unique=False)
        op.create_index(op.f('ix_auto_parsed_jobs_parsing_job_id'), 'auto_parsed_jobs', ['parsing_job_id'], unique=False)
    else:
        columns = [col['name'] for col in inspector.get_columns('auto_parsed_jobs')]
        if 'is_generated' not in columns:
            op.add_column(
                'auto_parsed_jobs',
                sa.Column('is_generated', sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if 'cover_letter_text' not in columns:
            op.add_column(
                'auto_parsed_jobs',
                sa.Column('cover_letter_text', sa.Text(), nullable=True),
            )


def downgrade() -> None:
    op.drop_column('auto_parsed_jobs', 'cover_letter_text')
    op.drop_column('auto_parsed_jobs', 'is_generated')
