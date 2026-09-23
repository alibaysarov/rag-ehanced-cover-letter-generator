import asyncio
import hashlib
import logging
from datetime import datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.helper import get_body_from_page, get_domain_by_url, secure_request_route
from app.models import ParserUsage, User
from app.pw_instances import chromium as chromium_module
from app.repository.parser_repository import ParserRepository
from app.schemas.vacancy.single_vacancy import SingleVacancy
from app.services.parser_catalog import ParserCatalogService
from app.services.scraper.parsers.configured import ConfiguredVacancyParser
from app.services.scraper.parsers.runtime_registry import create_runtime

logger = logging.getLogger(__name__)
SINGLE_PARSE_DEADLINE_SECONDS = 120


class VacancyScrapingService:
    """Request-scoped, user-aware parser catalog and single-URL extraction."""

    def __init__(self, session: AsyncSession, cache: Redis | None = None):
        self._session = session
        self._cache = cache

    async def parse_single(self, url: str, user_id: int) -> SingleVacancy:
        repository = ParserRepository(self._session)
        user = await self._session.scalar(
            select(User).where(User.id == user_id).with_for_update()
        )
        if user is None:
            raise LookupError("user not found")
        revision = user.parsers_revision
        cache_key = self._vacancy_cache_key(user_id, revision, url)
        if self._cache is not None:
            try:
                cached = await asyncio.wait_for(self._cache.get(cache_key), timeout=0.5)
                if cached:
                    await self._session.rollback()
                    return SingleVacancy.model_validate_json(cached)
            except Exception:
                logger.warning("Vacancy text cache read failed", exc_info=True)

        _, snapshots = await ParserCatalogService(
            self._session, self._cache
        ).get_catalog(user_id, revision)
        parser_map = {item.site_key: item for item in snapshots}
        domain = get_domain_by_url(url)
        snapshot = parser_map.get(domain.lower() if domain else "")
        usage: ParserUsage | None = None
        if snapshot is not None:
            persisted = await repository.get_owned(snapshot.id, user_id)
            if persisted is None:
                raise LookupError("parser was removed")
            usage = ParserUsage(
                parser_id=snapshot.id,
                user_id=user_id,
                expires_at=datetime.utcnow()
                + timedelta(seconds=SINGLE_PARSE_DEADLINE_SECONDS),
            )
            self._session.add(usage)
        await self._session.commit()

        page = None
        runtime = None
        try:

            async def extract() -> SingleVacancy:
                nonlocal page, runtime
                if snapshot is not None:
                    if (
                        snapshot.extraction_engine == "selectors_v1"
                        and snapshot.fetch_mode == "http"
                    ):
                        runtime = create_runtime(snapshot)
                        return await runtime.parse_single_by_url(url)
                    page = await chromium_module.chromium.new_page()
                    await page.route("**/*", secure_request_route)
                    if snapshot.extraction_engine == "selectors_v1":
                        runtime = create_runtime(snapshot, chromium_module.chromium)
                        return await runtime.parse_single_by_url(url)
                    return await ConfiguredVacancyParser(snapshot).parse_single_by_url(
                        page, url
                    )
                page = await chromium_module.chromium.new_page()
                await page.route("**/*", secure_request_route)
                body = await get_body_from_page(page, url)
                return SingleVacancy(job_title="", job_text=body, job_url=url)

            result = await asyncio.wait_for(
                extract(), timeout=SINGLE_PARSE_DEADLINE_SECONDS
            )
            if self._cache is not None:
                try:
                    await asyncio.wait_for(
                        self._cache.set(cache_key, result.model_dump_json(), ex=3600),
                        timeout=0.5,
                    )
                except Exception:
                    logger.warning("Vacancy text cache write failed", exc_info=True)
            return result
        finally:
            if runtime is not None:
                await runtime.aclose()
            if page is not None:
                await page.close()
            if usage is not None and usage.id is not None:
                stored = await self._session.get(ParserUsage, usage.id)
                if stored is not None:
                    await self._session.delete(stored)
                    await self._session.commit()

    @staticmethod
    def _vacancy_cache_key(user_id: int, revision: int, url: str) -> str:
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        return f"vacancy-text:v1:{user_id}:{revision}:{url_hash}"
