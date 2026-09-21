from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models import Parser, ParserUsage, ParsingSiteJob, User
from app.schemas.parser import ParserCreate, ParserUpdate, normalize_site_key


class ParserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock_user(self, user_id: int) -> User:
        user = await self.session.scalar(
            select(User).where(User.id == user_id).with_for_update()
        )
        if user is None:
            raise LookupError("user not found")
        return user

    async def list_all(self, user_id: int) -> list[Parser]:
        return list(
            (
                await self.session.scalars(
                    select(Parser)
                    .where(Parser.user_id == user_id)
                    .order_by(col(Parser.created_at).desc(), col(Parser.id).desc())
                )
            ).all()
        )

    async def list_page(
        self, user_id: int, page: int, page_size: int
    ) -> tuple[list[Parser], int]:
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Parser)
                .where(Parser.user_id == user_id)
            )
            or 0
        )
        items = list(
            (
                await self.session.scalars(
                    select(Parser)
                    .where(Parser.user_id == user_id)
                    .order_by(col(Parser.created_at).desc(), col(Parser.id).desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return items, total

    async def get_owned(self, parser_id: int, user_id: int) -> Parser | None:
        return await self.session.scalar(
            select(Parser).where(Parser.id == parser_id, Parser.user_id == user_id)
        )

    async def find_by_site_key(self, user_id: int, site_key: str) -> Parser | None:
        return await self.session.scalar(
            select(Parser).where(Parser.user_id == user_id, Parser.site_key == site_key)
        )

    async def create(self, user_id: int, payload: ParserCreate) -> tuple[Parser, int]:
        user = await self.lock_user(user_id)
        old_revision = user.parsers_revision
        parser = Parser(
            user_id=user_id,
            site_key=normalize_site_key(payload.base_url),
            **payload.model_dump(mode="python"),
        )
        self.session.add(parser)
        user.parsers_revision += 1
        await self.session.flush()
        return parser, old_revision

    async def update(
        self, parser_id: int, user_id: int, payload: ParserUpdate
    ) -> tuple[Parser | None, int | None, bool]:
        user = await self.lock_user(user_id)
        parser = await self.session.scalar(
            select(Parser)
            .where(Parser.id == parser_id, Parser.user_id == user_id)
            .with_for_update()
        )
        if parser is None:
            return None, None, False
        if parser.version != payload.version:
            return parser, None, True
        old_revision = user.parsers_revision
        for key, value in payload.model_dump(
            exclude={"version"}, mode="python"
        ).items():
            setattr(parser, key, value)
        parser.site_key = normalize_site_key(payload.base_url)
        parser.version += 1
        parser.updated_at = datetime.utcnow()
        user.parsers_revision += 1
        await self.session.flush()
        return parser, old_revision, False

    async def delete(
        self, parser_id: int, user_id: int
    ) -> tuple[bool, int | None, bool]:
        user = await self.lock_user(user_id)
        parser = await self.session.scalar(
            select(Parser)
            .where(Parser.id == parser_id, Parser.user_id == user_id)
            .with_for_update()
        )
        if parser is None:
            return False, None, False
        if await self.is_in_use(parser_id):
            return True, None, True
        old_revision = user.parsers_revision
        await self.session.delete(parser)
        user.parsers_revision += 1
        await self.session.flush()
        return True, old_revision, False

    async def in_use_ids(self, parser_ids: list[int]) -> set[int]:
        if not parser_ids:
            return set()
        now = datetime.utcnow()
        busy_jobs = await self.session.scalars(
            select(ParsingSiteJob.parser_id).where(
                col(ParsingSiteJob.parser_id).in_(parser_ids),
                col(ParsingSiteJob.status).in_(["pending", "running"]),
            )
        )
        busy_usages = await self.session.scalars(
            select(ParserUsage.parser_id).where(
                col(ParserUsage.parser_id).in_(parser_ids),
                col(ParserUsage.expires_at) > now,
            )
        )
        return {value for value in [*busy_jobs.all(), *busy_usages.all()] if value}

    async def is_in_use(self, parser_id: int) -> bool:
        return parser_id in await self.in_use_ids([parser_id])
