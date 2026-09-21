import unittest
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select

from app.core.config import settings
from app.models import AutoParsedJob, Parser, ParsingJob, ParsingSiteJob, User
from app.repository.parsing_job_repository import ParsingJobRepository
from app.services.scraper.parser_defaults import default_parser_values


@unittest.skipUnless(
    settings.DATABASE_URL, "DATABASE_URL is required for PostgreSQL test"
)
class ParsingJobRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = f"parsing_repo_{uuid.uuid4().hex}"
        self.admin_engine = create_async_engine(settings.DATABASE_URL)
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))

        self.engine = create_async_engine(
            settings.DATABASE_URL,
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        async with self.engine.begin() as connection:
            for table in (
                User.__table__,
                ParsingJob.__table__,
                Parser.__table__,
                ParsingSiteJob.__table__,
                AutoParsedJob.__table__,
            ):
                await connection.run_sync(table.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session:
            user = User(email="repository@example.test", password_hash="test")
            session.add(user)
            await session.commit()
            self.user_id = user.id
        self.repository = ParsingJobRepository(self.sessions)

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        await self.admin_engine.dispose()

    async def test_site_transitions_counters_and_final_status_are_serialized(self):
        job = await self.repository.create_job_with_sites(
            self.user_id, "python", ("hh.ru", "geekjob.ru")
        )
        self.assertIsNotNone(job.id)
        self.assertIsNotNone(await self.repository.claim_site(job.id, "hh.ru"))
        self.assertIsNone(await self.repository.claim_site(job.id, "hh.ru"))
        self.assertIsNotNone(await self.repository.claim_site(job.id, "geekjob.ru"))

        await self.repository.record_found(job.id, "hh.ru", 2)
        await self.repository.record_found(job.id, "geekjob.ru", 0)
        record, inserted = await self.repository.save_vacancy(
            job_id=job.id,
            site_key="hh.ru",
            user_id=self.user_id,
            vacancy_id="same-external-id",
            url="https://hh.ru/vacancy/1",
            job_title="Python developer",
            job_text="Text",
        )
        self.assertTrue(inserted)
        self.assertIsNotNone(record)
        _, duplicate_inserted = await self.repository.save_vacancy(
            job_id=job.id,
            site_key="hh.ru",
            user_id=self.user_id,
            vacancy_id="same-external-id",
            url="https://hh.ru/vacancy/1",
            job_title="Changed title must not overwrite",
            job_text="Changed text",
        )
        self.assertFalse(duplicate_inserted)
        await self.repository.record_vacancy_failure(job.id, "hh.ru")
        await self.repository.finish_site(
            job.id, "hh.ru", failed=True, error="detail failed"
        )

        async with self.sessions() as session:
            parent = await session.get(ParsingJob, job.id)
            self.assertEqual("running", parent.status)
            self.assertEqual(2, parent.total_found)
            self.assertEqual(1, parent.saved_count)

        await self.repository.finish_site(job.id, "geekjob.ru")
        async with self.sessions() as session:
            parent = await session.get(ParsingJob, job.id)
            sites = list((await session.scalars(select(ParsingSiteJob))).all())
            saved = list((await session.scalars(select(AutoParsedJob))).all())
            self.assertEqual("failed", parent.status)
            self.assertIn("hh.ru: detail failed", parent.error)
            self.assertIsNotNone(parent.finished_at)
            self.assertEqual([0, 1], sorted(site.saved_count for site in sites))
            self.assertEqual(1, len(saved))

    async def test_empty_sites_and_dispatch_failure_finalize_only_after_running_site(
        self,
    ):
        empty_job = await self.repository.create_job_with_sites(
            self.user_id, "empty", ("hh.ru", "geekjob.ru")
        )
        await self.repository.claim_site(empty_job.id, "hh.ru")
        await self.repository.claim_site(empty_job.id, "geekjob.ru")
        await self.repository.record_found(empty_job.id, "hh.ru", 0)
        await self.repository.record_found(empty_job.id, "geekjob.ru", 0)
        await self.repository.finish_site(empty_job.id, "hh.ru")
        await self.repository.finish_site(empty_job.id, "geekjob.ru")
        async with self.sessions() as session:
            self.assertEqual(
                "done", (await session.get(ParsingJob, empty_job.id)).status
            )

        dispatch_job = await self.repository.create_job_with_sites(
            self.user_id, "dispatch", ("hh.ru", "geekjob.ru")
        )
        await self.repository.claim_site(dispatch_job.id, "hh.ru")
        await self.repository.fail_pending_dispatch(dispatch_job.id, "dispatch failure")
        async with self.sessions() as session:
            self.assertEqual(
                "running", (await session.get(ParsingJob, dispatch_job.id)).status
            )
        await self.repository.finish_site(dispatch_job.id, "hh.ru")
        async with self.sessions() as session:
            final = await session.get(ParsingJob, dispatch_job.id)
            self.assertEqual("failed", final.status)
            self.assertIn("geekjob.ru: dispatch failure", final.error)

    async def test_vacancy_limits_are_persisted_for_workers(self):
        async with self.sessions() as session:
            session.add_all(
                [Parser(**item) for item in default_parser_values(self.user_id)]
            )
            await session.commit()

        _, sites = await self.repository.create_job_with_parsers(
            self.user_id, "python", vacancy_limit=3
        )
        self.assertEqual([2, 1], [site.vacancy_limit for site in sites])
        for site in sites:
            claimed = await self.repository.claim_site_by_id(site.id)
            self.assertEqual(site.vacancy_limit, claimed.vacancy_limit)

    async def test_catalog_is_frozen_into_site_job_snapshots(self):
        with self.assertRaisesRegex(ValueError, "parsers_empty"):
            await self.repository.create_job_with_parsers(self.user_id, "python")

        async with self.sessions() as session:
            parsers = [Parser(**item) for item in default_parser_values(self.user_id)]
            session.add_all(parsers)
            await session.commit()

        job, sites = await self.repository.create_job_with_parsers(
            self.user_id, "python"
        )
        self.assertEqual(2, len(sites))
        self.assertTrue(all(site.parser_snapshot for site in sites))
        hh_site = next(site for site in sites if site.site_key == "hh.ru")
        self.assertEqual(1, hh_site.parser_snapshot["version"])
        self.assertEqual("hh.ru", hh_site.parser_snapshot["site_key"])

        async with self.sessions() as session:
            hh = await session.get(Parser, hh_site.parser_id)
            hh.name = "Changed later"
            hh.version += 1
            await session.commit()
            stored = await session.get(ParsingSiteJob, hh_site.id)
            self.assertEqual("hh.ru", stored.parser_snapshot["name"])
            self.assertEqual(job.id, stored.parsing_job_id)


if __name__ == "__main__":
    unittest.main()
