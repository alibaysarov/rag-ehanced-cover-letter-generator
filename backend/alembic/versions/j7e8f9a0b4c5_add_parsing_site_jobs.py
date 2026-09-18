"""add parsing site jobs

Revision ID: j7e8f9a0b4c5
Revises: d9c8149460e0, i6d7e8f9a3b4
Create Date: 2026-09-18 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "j7e8f9a0b4c5"
down_revision: Union[str, Sequence[str], None] = ("d9c8149460e0", "i6d7e8f9a3b4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parsing_site_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "parsing_job_id",
            sa.Integer(),
            sa.ForeignKey("parsing_jobs.id"),
            nullable=False,
        ),
        sa.Column("site_key", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("total_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("saved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "parsing_job_id", "site_key", name="uq_parsing_site_jobs_job_site"
        ),
    )
    op.create_index(
        "ix_parsing_site_jobs_parsing_job_id",
        "parsing_site_jobs",
        ["parsing_job_id"],
    )
    op.add_column(
        "auto_parsed_jobs",
        sa.Column("parsing_site_job_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_auto_parsed_jobs_parsing_site_job_id",
        "auto_parsed_jobs",
        ["parsing_site_job_id"],
    )
    op.create_foreign_key(
        "fk_auto_parsed_jobs_parsing_site_job_id",
        "auto_parsed_jobs",
        "parsing_site_jobs",
        ["parsing_site_job_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_auto_parsed_jobs_site_vacancy",
        "auto_parsed_jobs",
        ["parsing_site_job_id", "vacancy_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_auto_parsed_jobs_site_vacancy",
        "auto_parsed_jobs",
        type_="unique",
    )
    op.drop_constraint(
        "fk_auto_parsed_jobs_parsing_site_job_id",
        "auto_parsed_jobs",
        type_="foreignkey",
    )
    op.drop_index("ix_auto_parsed_jobs_parsing_site_job_id", "auto_parsed_jobs")
    op.drop_column("auto_parsed_jobs", "parsing_site_job_id")
    op.drop_index("ix_parsing_site_jobs_parsing_job_id", "parsing_site_jobs")
    op.drop_table("parsing_site_jobs")
