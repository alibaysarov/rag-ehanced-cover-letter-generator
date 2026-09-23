"""Seed user-owned parser configurations from a CSV export."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import select

from app.database import async_session_maker
from app.models import Parser, User
from app.schemas.parser import ParserCreate, normalize_site_key

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "seed_data" / "parsers.csv"
REQUIRED_COLUMNS = {
    "name",
    "base_url",
    "single_url",
    "has_pagination",
    "evaluate_vacancy_list",
    "evaluate_vacancy_page",
    "evaluate_pagination",
    "format_url",
    "pagination_start",
    "max_pages",
    "extraction_engine",
    "fetch_mode",
    "request_config",
    "extraction_config",
}


def parse_bool(value: str, field: str, row_number: int) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"row {row_number}: {field} must be true or false")


def parse_int(value: str, field: str, row_number: int) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {field} must be an integer") from exc


def parse_json(value: str, field: str, row_number: int) -> Any:
    if not value.strip():
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"row {row_number}: {field} contains invalid JSON") from exc


def row_to_parser(row: dict[str, str], user_id: int, row_number: int) -> Parser:
    payload = ParserCreate.model_validate(
        {
            "name": row["name"],
            "base_url": row["base_url"],
            "single_url": row["single_url"],
            "has_pagination": parse_bool(
                row["has_pagination"], "has_pagination", row_number
            ),
            "evaluate_vacancy_list": row["evaluate_vacancy_list"],
            "evaluate_vacancy_page": row["evaluate_vacancy_page"],
            "evaluate_pagination": row["evaluate_pagination"].strip() or None,
            "format_url": parse_json(row["format_url"], "format_url", row_number),
            "pagination_start": parse_int(
                row["pagination_start"], "pagination_start", row_number
            ),
            "max_pages": parse_int(row["max_pages"], "max_pages", row_number),
            "extraction_engine": row["extraction_engine"],
            "fetch_mode": row["fetch_mode"],
            "request_config": parse_json(
                row["request_config"], "request_config", row_number
            ),
            "extraction_config": parse_json(
                row["extraction_config"], "extraction_config", row_number
            ),
        }
    )
    return Parser(
        user_id=user_id,
        site_key=normalize_site_key(payload.base_url),
        **payload.model_dump(mode="python"),
    )


def read_rows(csv_path: Path) -> list[tuple[int, dict[str, str]]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or ())
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(missing))}"
            )
        return [(line_number, row) for line_number, row in enumerate(reader, start=2)]


def upgrade_parser(existing: Parser, incoming: Parser) -> None:
    for field in (
        "name",
        "base_url",
        "single_url",
        "has_pagination",
        "evaluate_vacancy_list",
        "evaluate_vacancy_page",
        "evaluate_pagination",
        "format_url",
        "pagination_start",
        "max_pages",
        "extraction_engine",
        "fetch_mode",
        "request_config",
        "extraction_config",
    ):
        setattr(existing, field, getattr(incoming, field))
    existing.version += 1
    existing.updated_at = datetime.utcnow()


async def seed(
    csv_path: Path,
    user_id: int | None,
    email: str | None,
    dry_run: bool,
) -> tuple[int, int, int]:
    rows = read_rows(csv_path)
    async with async_session_maker() as session:
        user = (
            await session.get(User, user_id)
            if user_id is not None
            else await session.scalar(select(User).where(User.email == email))
        )
        if user is None or user.id is None:
            identity = f"{user_id}" if user_id is not None else repr(email)
            raise ValueError(f"user {identity} does not exist")
        user_id = user.id

        existing_parsers = {
            parser.site_key: parser
            for parser in (
                await session.scalars(select(Parser).where(Parser.user_id == user_id))
            ).all()
        }
        pending_site_keys: set[str] = set()
        parsers: list[Parser] = []
        updated = 0
        skipped = 0

        for row_number, row in rows:
            parser = row_to_parser(row, user_id, row_number)
            existing = existing_parsers.get(parser.site_key)
            if existing is not None:
                if (
                    parser.extraction_engine == "selectors_v1"
                    and existing.extraction_engine != "selectors_v1"
                ):
                    if not dry_run:
                        upgrade_parser(existing, parser)
                        user.parsers_revision += 1
                    updated += 1
                else:
                    skipped += 1
                continue
            if parser.site_key in pending_site_keys:
                skipped += 1
                continue
            pending_site_keys.add(parser.site_key)
            parsers.append(parser)

        if not dry_run:
            session.add_all(parsers)
            await session.commit()

        return len(parsers), updated, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import user-owned parsers from a CSV export. "
            "Existing site_key values are skipped."
        )
    )
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument(
        "--user-id", type=int, help="Existing user ID that will own the parsers"
    )
    identity.add_argument(
        "--email", help="Email of the existing user that will own the parsers"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV path (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and count imports without writing to the database",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    created, updated, skipped = await seed(
        args.csv, args.user_id, args.email, args.dry_run
    )
    action = "would import" if args.dry_run else "imported"
    print(
        f"{action} {created} parser(s); updated {updated}; "
        f"skipped {skipped} existing parser(s)"
    )


if __name__ == "__main__":
    asyncio.run(main())
