"""edit_cv_table_alter_source_id_column

Revision ID: 992d76276b2f
Revises: 
Create Date: 2026-01-07 15:54:08.238177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '992d76276b2f'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'cvs',
        'source_id',
        existing_type=sa.Integer(),
        type_=sa.String(length=255),
        existing_nullable=False,
        postgresql_using='source_id::text'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'cvs',
        'source_id',
        existing_type=sa.String(length=255),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using='source_id::integer'
    )
