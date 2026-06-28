"""create_auto_parsed_jobs_table

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
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
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['parsing_job_id'], ['parsing_jobs.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_auto_parsed_jobs_user_id'), 'auto_parsed_jobs', ['user_id'], unique=False)
        op.create_index(op.f('ix_auto_parsed_jobs_parsing_job_id'), 'auto_parsed_jobs', ['parsing_job_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_auto_parsed_jobs_parsing_job_id'), table_name='auto_parsed_jobs')
    op.drop_index(op.f('ix_auto_parsed_jobs_user_id'), table_name='auto_parsed_jobs')
    op.drop_table('auto_parsed_jobs')
