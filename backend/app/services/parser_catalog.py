import asyncio
import json
import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repository.parser_repository import ParserRepository
from app.schemas.parser import ParserSnapshot

logger = logging.getLogger(__name__)
CACHE_TIMEOUT_SECONDS = 0.5


class ParserCatalogService:
    def __init__(self, session: AsyncSession, cache: Redis | None = None):
        self.session = session
        self.repository = ParserRepository(session)
        self.cache = cache

    @staticmethod
    def cache_key(user_id: int, revision: int) -> str:
        return f"parsers:v1:{user_id}:{revision}"

    async def revision(self, user_id: int) -> int:
        revision = await self.session.get(User, user_id)
        if revision is None:
            raise LookupError("user not found")
        return revision.parsers_revision

    async def get_catalog(
        self, user_id: int, revision: int | None = None
    ) -> tuple[int, tuple[ParserSnapshot, ...]]:
        current_revision = (
            await self.revision(user_id) if revision is None else revision
        )
        key = self.cache_key(user_id, current_revision)
        if self.cache is not None:
            try:
                cached = await asyncio.wait_for(
                    self.cache.get(key), timeout=CACHE_TIMEOUT_SECONDS
                )
                if cached is not None:
                    values = json.loads(cached)
                    return current_revision, tuple(
                        ParserSnapshot.model_validate(value) for value in values
                    )
            except Exception:
                logger.warning("Parser catalog cache read failed", exc_info=True)
        parsers = await self.repository.list_all(user_id)
        snapshots = tuple(ParserSnapshot.model_validate(parser) for parser in parsers)
        if self.cache is not None:
            try:
                await asyncio.wait_for(
                    self.cache.set(
                        key,
                        json.dumps(
                            [item.model_dump(mode="json") for item in snapshots]
                        ),
                        ex=3600,
                    ),
                    timeout=CACHE_TIMEOUT_SECONDS,
                )
            except Exception:
                logger.warning("Parser catalog cache write failed", exc_info=True)
        return current_revision, snapshots

    async def invalidate(self, user_id: int, old_revision: int | None) -> None:
        if self.cache is None or old_revision is None:
            return
        try:
            await asyncio.wait_for(
                self.cache.delete(self.cache_key(user_id, old_revision)),
                timeout=CACHE_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.warning("Parser catalog cache invalidation failed", exc_info=True)
