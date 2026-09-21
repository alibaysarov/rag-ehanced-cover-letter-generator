"""Compatibility bridge for databases stamped by the early generation-mode build.

Revision ID: k8f9a0b1c5d6
Revises: j7e8f9a0b4c5
"""

revision = "k8f9a0b1c5d6"
down_revision = "j7e8f9a0b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The legacy revision was deployed without a migration file.  It made no
    # schema changes, so this node only restores the missing Alembic history.
    pass


def downgrade() -> None:
    pass
