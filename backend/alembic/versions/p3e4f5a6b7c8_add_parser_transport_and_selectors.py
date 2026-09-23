"""add parser transport and selector configuration

Revision ID: p3e4f5a6b7c8
Revises: o2d3e4f5a6b7
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "p3e4f5a6b7c8"
down_revision = "o2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parsers", sa.Column("extraction_engine", sa.String(32), nullable=False, server_default="legacy_js"))
    op.add_column("parsers", sa.Column("fetch_mode", sa.String(32), nullable=False, server_default="playwright"))
    op.add_column("parsers", sa.Column("request_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("parsers", sa.Column("extraction_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_check_constraint("ck_parsers_extraction_engine", "parsers", "extraction_engine IN ('legacy_js', 'selectors_v1')")
    op.create_check_constraint("ck_parsers_fetch_mode", "parsers", "fetch_mode IN ('http', 'playwright')")
    op.create_check_constraint("ck_parsers_engine_transport", "parsers", "extraction_engine <> 'legacy_js' OR fetch_mode = 'playwright'")
    op.create_check_constraint("ck_parsers_selector_config", "parsers", "(extraction_engine = 'legacy_js' AND extraction_config IS NULL) OR (extraction_engine = 'selectors_v1' AND extraction_config IS NOT NULL)")


def downgrade() -> None:
    for name in ("ck_parsers_selector_config", "ck_parsers_engine_transport", "ck_parsers_fetch_mode", "ck_parsers_extraction_engine"):
        op.drop_constraint(name, "parsers", type_="check")
    for name in ("extraction_config", "request_config", "fetch_mode", "extraction_engine"):
        op.drop_column("parsers", name)
