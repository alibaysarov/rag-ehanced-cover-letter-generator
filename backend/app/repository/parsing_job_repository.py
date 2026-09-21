from datetime import datetime
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models import AutoParsedJob, Parser, ParsingJob, ParsingSiteJob, User
from app.schemas.generation_mode import GenerationMode
from app.schemas.parser import ParserSnapshot

SessionFactory = Callable[[], AsyncSession]
TERMINAL_SITE_STATUSES = {"done", "failed"}


class ParsingJobRepository:
    """State changes for a parsing job, each in its own short transaction."""

    def __init__(self, session_factory: SessionFactory):
        self._session_factory = session_factory

    async def create_job_with_sites(
        self,
        user_id: int,
        query: str,
        site_keys: tuple[str, ...],
        generation_mode: GenerationMode = GenerationMode.AI,
    ) -> ParsingJob:
        async with self._session_factory() as session, session.begin():
            job = ParsingJob(
                user_id=user_id,
                query=query,
                status="pending",
                generation_mode=generation_mode,
            )
            session.add(job)
            await session.flush()
            if job.id is None:
                raise RuntimeError("Parsing job was not assigned an id")
            session.add_all(
                [
                    ParsingSiteJob(parsing_job_id=job.id, site_key=site_key)
                    for site_key in site_keys
                ]
            )
        return job

    async def create_job_with_parsers(
        self,
        user_id: int,
        query: str,
        generation_mode: GenerationMode = GenerationMode.AI,
        *,
        vacancy_limit: int | None = None,
    ) -> tuple[ParsingJob, list[ParsingSiteJob]]:
        """Freeze parser snapshots and distribute this run's vacancy budget."""
        if vacancy_limit is not None and vacancy_limit < 1:
            raise ValueError("vacancy_limit must be positive")
        async with self._session_factory() as session, session.begin():
            user = await session.scalar(
                select(User).where(User.id == user_id).with_for_update()
            )
            if user is None:
                raise LookupError("user not found")
            parsers = list(
                (
                    await session.scalars(
                        select(Parser)
                        .where(Parser.user_id == user_id)
                        .order_by(col(Parser.created_at).desc(), col(Parser.id).desc())
                    )
                ).all()
            )
            if not parsers:
                raise ValueError("parsers_empty")
            per_site_limit = (
                (vacancy_limit + len(parsers) - 1) // len(parsers)
                if vacancy_limit is not None
                else None
            )
            remaining = vacancy_limit
            job = ParsingJob(
                user_id=user_id,
                query=query,
                status="pending",
                generation_mode=generation_mode,
            )
            session.add(job)
            await session.flush()
            if job.id is None:
                raise RuntimeError("Parsing job was not assigned an id")
            sites = []
            for parser in parsers:
                if remaining == 0:
                    break
                site_limit = (
                    min(per_site_limit, remaining)
                    if per_site_limit is not None and remaining is not None
                    else None
                )
                snapshot = ParserSnapshot.model_validate(parser).model_dump(mode="json")
                site = ParsingSiteJob(
                    parsing_job_id=job.id,
                    site_key=parser.site_key,
                    parser_id=parser.id,
                    parser_version=parser.version,
                    parser_snapshot=snapshot,
                    vacancy_limit=site_limit,
                )
                session.add(site)
                sites.append(site)
                if remaining is not None and site_limit is not None:
                    remaining -= site_limit
            await session.flush()
        return job, sites

    async def set_auto_generation_error(self, job_id: int, error: str | None) -> None:
        async with self._session_factory() as session, session.begin():
            job = await self._locked_job(session, job_id)
            if job is not None:
                job.auto_generation_error = error

    async def record_template_generation_started(self, job_id: int) -> None:
        """Record the first successfully dispatched per-vacancy template task."""
        async with self._session_factory() as session, session.begin():
            job = await self._locked_job(session, job_id)
            if job is None:
                raise LookupError(f"Parsing job {job_id} does not exist")
            if job.generation_mode != GenerationMode.TEMPLATE:
                raise ValueError("Template generation is not enabled for this job")
            if job.auto_generation_started_at is None:
                job.auto_generation_started_at = datetime.utcnow()

    async def claim_site(self, job_id: int, site_key: str) -> ParsingSiteJob | None:
        async with self._session_factory() as session, session.begin():
            job = await self._locked_job(session, job_id)
            if job is None:
                return None
            site = await self._locked_site(session, job_id, site_key)
            if site is None or site.status != "pending":
                return None

            site.status = "running"
            site.started_at = datetime.utcnow()
            if job.status == "pending":
                job.status = "running"
            return site

    async def claim_site_by_id(self, site_job_id: int) -> ParsingSiteJob | None:
        async with self._session_factory() as session, session.begin():
            site = await session.scalar(
                select(ParsingSiteJob)
                .where(ParsingSiteJob.id == site_job_id)
                .with_for_update()
            )
            if site is None or site.status != "pending":
                return None
            job = await self._locked_job(session, site.parsing_job_id)
            if job is None:
                return None
            site.status = "running"
            site.started_at = datetime.utcnow()
            if job.status == "pending":
                job.status = "running"
            return site

    async def get_job(self, job_id: int) -> ParsingJob | None:
        async with self._session_factory() as session:
            return await session.get(ParsingJob, job_id)

    async def record_found(self, job_id: int, site_key: str, total_found: int) -> None:
        if total_found < 0:
            raise ValueError("total_found must not be negative")
        async with self._session_factory() as session, session.begin():
            job = await self._require_locked_job(session, job_id)
            site = await self._require_locked_site(session, job_id, site_key)
            if site.status in TERMINAL_SITE_STATUSES or site.total_found != 0:
                return
            site.total_found = total_found
            job.total_found += total_found

    async def save_vacancy(
        self,
        *,
        job_id: int,
        site_key: str,
        user_id: int,
        vacancy_id: str,
        url: str,
        job_title: str,
        job_text: str,
        company_name: str | None = None,
    ) -> tuple[AutoParsedJob | None, bool]:
        if not vacancy_id:
            raise ValueError("vacancy_id is required")

        async with self._session_factory() as session, session.begin():
            job = await self._require_locked_job(session, job_id)
            site = await self._require_locked_site(session, job_id, site_key)
            existing = await session.scalar(
                select(AutoParsedJob)
                .where(AutoParsedJob.parsing_site_job_id == site.id)
                .where(AutoParsedJob.vacancy_id == vacancy_id)
            )
            if existing is not None:
                return existing, False

            if job.id is None or site.id is None:
                raise RuntimeError("Persisted parsing job is missing an id")

            record = AutoParsedJob(
                user_id=user_id,
                parsing_job_id=job.id,
                parsing_site_job_id=site.id,
                vacancy_id=vacancy_id,
                url=url,
                job_title=job_title,
                job_text=job_text,
                company_name=company_name,
                web_site=site_key,
                is_applied=False,
                is_viewed=False,
                is_generated=False,
                cover_letter_text="",
            )
            session.add(record)
            await session.flush()
            site.saved_count += 1
            job.saved_count += 1
            return record, True

    async def record_vacancy_failure(self, job_id: int, site_key: str) -> None:
        async with self._session_factory() as session, session.begin():
            await self._require_locked_job(session, job_id)
            site = await self._require_locked_site(session, job_id, site_key)
            if site.status not in TERMINAL_SITE_STATUSES:
                site.failed_count += 1

    async def finish_site(
        self,
        job_id: int,
        site_key: str,
        *,
        failed: bool = False,
        error: str | None = None,
    ) -> ParsingJob | None:
        async with self._session_factory() as session, session.begin():
            job = await self._require_locked_job(session, job_id)
            site = await self._require_locked_site(session, job_id, site_key)
            if site.status in TERMINAL_SITE_STATUSES:
                return job

            site.status = "failed" if failed else "done"
            site.error = error if failed else None
            site.finished_at = datetime.utcnow()
            await self._finish_parent_if_ready(session, job)
            return job

    async def fail_pending_dispatch(self, job_id: int, error: str) -> ParsingJob | None:
        async with self._session_factory() as session, session.begin():
            job = await self._locked_job(session, job_id)
            if job is None:
                return None
            sites = list(
                (
                    await session.scalars(
                        select(ParsingSiteJob)
                        .where(ParsingSiteJob.parsing_job_id == job_id)
                        .with_for_update()
                    )
                ).all()
            )
            now = datetime.utcnow()
            for site in sites:
                if site.status == "pending":
                    site.status = "failed"
                    site.error = error
                    site.finished_at = now
            await self._finish_parent_if_ready(session, job, sites)
            return job

    async def _locked_job(
        self, session: AsyncSession, job_id: int
    ) -> ParsingJob | None:
        return await session.scalar(
            select(ParsingJob).where(ParsingJob.id == job_id).with_for_update()
        )

    async def _locked_site(
        self, session: AsyncSession, job_id: int, site_key: str
    ) -> ParsingSiteJob | None:
        return await session.scalar(
            select(ParsingSiteJob)
            .where(ParsingSiteJob.parsing_job_id == job_id)
            .where(ParsingSiteJob.site_key == site_key)
            .with_for_update()
        )

    async def _require_locked_job(
        self, session: AsyncSession, job_id: int
    ) -> ParsingJob:
        job = await self._locked_job(session, job_id)
        if job is None:
            raise LookupError(f"Parsing job {job_id} does not exist")
        return job

    async def _require_locked_site(
        self, session: AsyncSession, job_id: int, site_key: str
    ) -> ParsingSiteJob:
        site = await self._locked_site(session, job_id, site_key)
        if site is None:
            raise LookupError(f"Parsing site job {job_id}/{site_key} does not exist")
        return site

    async def _finish_parent_if_ready(
        self,
        session: AsyncSession,
        job: ParsingJob,
        sites: list[ParsingSiteJob] | None = None,
    ) -> None:
        if sites is None:
            sites = list(
                (
                    await session.scalars(
                        select(ParsingSiteJob)
                        .where(ParsingSiteJob.parsing_job_id == job.id)
                        .with_for_update()
                    )
                ).all()
            )
        if not sites or any(
            site.status not in TERMINAL_SITE_STATUSES for site in sites
        ):
            return

        failed_sites = [site for site in sites if site.status == "failed"]
        job.status = "failed" if failed_sites else "done"
        job.finished_at = datetime.utcnow()
        job.error = (
            "; ".join(
                f"{site.site_key}: {site.error or 'parsing failed'}"
                for site in failed_sites
            )
            if failed_sites
            else None
        )
