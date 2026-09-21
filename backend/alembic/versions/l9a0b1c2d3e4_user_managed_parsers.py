"""user managed vacancy parsers

Revision ID: l9a0b1c2d3e4
Revises: k8a9b0c1d2e3
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "l9a0b1c2d3e4"
down_revision = "k8a9b0c1d2e3"
branch_labels = None
depends_on = None

HH_LIST_JS = r"""
        
            () => [...document.querySelectorAll('[data-qa^=vacancy-serp__vacancy]')]
                    .map(v => {
                        const title = v.querySelector('[data-qa=serp-item__title-text]')?.textContent || null;
                        
                        const link = v.querySelector('a')?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/(\d+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
        """
HH_PAGE_JS = """
        ()=>{
            const job_title = document.querySelector('[data-qa="vacancy-title"]')?.textContent?.trim() || '';
            const job_text = document.querySelector('[data-qa="vacancy-description"]')?.textContent?.trim() || '';
            return {
                job_title,
                job_text,
            }
        }
        """
PAGINATION_JS = """
        () => [...document.querySelectorAll('[data-qa="pager-page"]')]
                .map(item => item.textContent?.trim() || null)
                .filter(v => v != null)
        """
GEEKJOB_LIST_JS = r"""
            () => [...document.querySelectorAll('ul.collection.serp-list li')]
                    .map(v => {
                        const elem = v.querySelector('p.truncate.vacancy-name a')
                        const title = elem?.textContent || null;
                        const link = elem?.href || null;
                        const vacancy_id = link?.match(/\/vacancy\/([^/?#]+)/)?.[1] || null;

                        return { title, link, vacancy_id };
                    })
                    .filter(({ title, vacancy_id, link }) => title && vacancy_id && link)
        """
GEEKJOB_PAGE_JS = """
        ()=>{
            const job_title = (
                document.querySelector('h1')?.textContent?.trim() ||
                document.querySelector('main h1')?.textContent?.trim() ||
                ''
            );

            const job_text = (
                document.querySelector('article')?.textContent?.trim() ||
                document.querySelector('[class*="description"]')?.textContent?.trim() ||
                document.body?.textContent?.trim() ||
                ''
            );

            return {
                job_title,
                job_text,
            }
        }
        """


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("parsers_revision", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_table(
        "parsers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("site_key", sa.String(255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("single_url", sa.Text(), nullable=False),
        sa.Column("has_pagination", sa.Boolean(), nullable=False),
        sa.Column("evaluate_vacancy_list", sa.Text(), nullable=False),
        sa.Column("evaluate_vacancy_page", sa.Text(), nullable=False),
        sa.Column("evaluate_pagination", sa.Text(), nullable=True),
        sa.Column("format_url", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pagination_start", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("pagination_start >= 0", name="ck_parsers_pagination_start"),
        sa.CheckConstraint("max_pages >= 1 AND max_pages <= 50", name="ck_parsers_max_pages"),
        sa.UniqueConstraint("user_id", "site_key", name="uq_parsers_user_site_key"),
    )
    op.create_index("ix_parsers_user_id", "parsers", ["user_id"])
    op.create_index(
        "ix_parsers_user_created_id",
        "parsers",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.add_column("parsing_site_jobs", sa.Column("parser_id", sa.Integer(), nullable=True))
    op.add_column("parsing_site_jobs", sa.Column("parser_version", sa.Integer(), nullable=True))
    op.add_column(
        "parsing_site_jobs",
        sa.Column("parser_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_parsing_site_jobs_parser_id",
        "parsing_site_jobs",
        "parsers",
        ["parser_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_parsing_site_jobs_parser_status",
        "parsing_site_jobs",
        ["parser_id", "status"],
    )
    op.create_table(
        "parser_usages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "parser_id",
            sa.Integer(),
            sa.ForeignKey("parsers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_parser_usages_parser_expires", "parser_usages", ["parser_id", "expires_at"]
    )

    parser_table = sa.table(
        "parsers",
        sa.column("user_id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("site_key", sa.String()),
        sa.column("base_url", sa.Text()),
        sa.column("single_url", sa.Text()),
        sa.column("has_pagination", sa.Boolean()),
        sa.column("evaluate_vacancy_list", sa.Text()),
        sa.column("evaluate_vacancy_page", sa.Text()),
        sa.column("evaluate_pagination", sa.Text()),
        sa.column("format_url", postgresql.JSONB()),
        sa.column("pagination_start", sa.Integer()),
        sa.column("max_pages", sa.Integer()),
    )
    users = [row[0] for row in op.get_bind().execute(sa.text("SELECT id FROM users"))]
    for user_id in users:
        op.bulk_insert(
            parser_table,
            [
                {
                    "user_id": user_id,
                    "name": "hh.ru",
                    "site_key": "hh.ru",
                    "base_url": "https://hh.ru/search/vacancy",
                    "single_url": "https://hh.ru/vacancy/{vacancy_id}",
                    "has_pagination": True,
                    "evaluate_vacancy_list": HH_LIST_JS,
                    "evaluate_vacancy_page": HH_PAGE_JS,
                    "evaluate_pagination": PAGINATION_JS,
                    "format_url": {"url_template": "{base_url}", "query_params": {"text": "{text}", "page": "{page}"}},
                    "pagination_start": 0,
                    "max_pages": 5,
                },
                {
                    "user_id": user_id,
                    "name": "geekjob.ru",
                    "site_key": "geekjob.ru",
                    "base_url": "https://geekjob.ru/vacancies",
                    "single_url": "https://geekjob.ru/vacancy/{vacancy_id}",
                    "has_pagination": False,
                    "evaluate_vacancy_list": GEEKJOB_LIST_JS,
                    "evaluate_vacancy_page": GEEKJOB_PAGE_JS,
                    "evaluate_pagination": PAGINATION_JS,
                    "format_url": {"url_template": "{base_url}", "query_params": {"qs": "{text}", "page": "{page}"}},
                    "pagination_start": 0,
                    "max_pages": 5,
                },
            ],
        )
    op.execute(sa.text("UPDATE users SET parsers_revision = 1"))


def downgrade() -> None:
    op.drop_index("ix_parser_usages_parser_expires", table_name="parser_usages")
    op.drop_table("parser_usages")
    op.drop_index("ix_parsing_site_jobs_parser_status", table_name="parsing_site_jobs")
    op.drop_constraint("fk_parsing_site_jobs_parser_id", "parsing_site_jobs", type_="foreignkey")
    op.drop_column("parsing_site_jobs", "parser_snapshot")
    op.drop_column("parsing_site_jobs", "parser_version")
    op.drop_column("parsing_site_jobs", "parser_id")
    op.drop_index("ix_parsers_user_created_id", table_name="parsers")
    op.drop_index("ix_parsers_user_id", table_name="parsers")
    op.drop_table("parsers")
    op.drop_column("users", "parsers_revision")
