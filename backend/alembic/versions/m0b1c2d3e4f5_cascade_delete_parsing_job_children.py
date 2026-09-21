"""cascade delete parsing job children

Revision ID: m0b1c2d3e4f5
Revises: l9a0b1c2d3e4
Create Date: 2026-09-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "m0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "l9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "auto_parsed_jobs_parsing_job_id_fkey",
        "auto_parsed_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "auto_parsed_jobs_parsing_job_id_fkey",
        "auto_parsed_jobs",
        "parsing_jobs",
        ["parsing_job_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "parsing_site_jobs_parsing_job_id_fkey",
        "parsing_site_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "parsing_site_jobs_parsing_job_id_fkey",
        "parsing_site_jobs",
        "parsing_jobs",
        ["parsing_job_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "fk_auto_parsed_jobs_parsing_site_job_id",
        "auto_parsed_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_auto_parsed_jobs_parsing_site_job_id",
        "auto_parsed_jobs",
        "parsing_site_jobs",
        ["parsing_site_job_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_auto_parsed_jobs_parsing_site_job_id",
        "auto_parsed_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_auto_parsed_jobs_parsing_site_job_id",
        "auto_parsed_jobs",
        "parsing_site_jobs",
        ["parsing_site_job_id"],
        ["id"],
    )

    op.drop_constraint(
        "parsing_site_jobs_parsing_job_id_fkey",
        "parsing_site_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "parsing_site_jobs_parsing_job_id_fkey",
        "parsing_site_jobs",
        "parsing_jobs",
        ["parsing_job_id"],
        ["id"],
    )

    op.drop_constraint(
        "auto_parsed_jobs_parsing_job_id_fkey",
        "auto_parsed_jobs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "auto_parsed_jobs_parsing_job_id_fkey",
        "auto_parsed_jobs",
        "parsing_jobs",
        ["parsing_job_id"],
        ["id"],
    )
