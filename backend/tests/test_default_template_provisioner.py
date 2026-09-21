import unittest
import uuid

from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select

from app.core.config import settings
from app.domain import TemplateCase, TemplateStatus
from app.models import AutoParsedJob, CoverLetterTemplate, LetterPhrase, Project, User
from app.services.default_template_provisioner import DefaultTemplateProvisioner
from app.services.template_generation import (
    TemplateConfigurationError,
    TemplateGenerationService,
)


@unittest.skipUnless(settings.DATABASE_URL, "DATABASE_URL is required")
class DefaultTemplateProvisionerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = f"template_defaults_{uuid.uuid4().hex}"
        self.admin_engine = create_async_engine(settings.DATABASE_URL)
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        await self.admin_engine.dispose()

    async def test_creates_four_active_templates_once(self):
        async with self.sessions() as session:
            user = User(email="defaults@example.test", password_hash="test")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            self.assertTrue(
                await DefaultTemplateProvisioner(session).ensure_for_user(user.id)
            )
            self.assertFalse(
                await DefaultTemplateProvisioner(session).ensure_for_user(user.id)
            )
            templates = list(
                (
                    await session.scalars(
                        select(CoverLetterTemplate).where(
                            CoverLetterTemplate.user_id == user.id
                        )
                    )
                ).all()
            )
            self.assertEqual(len(templates), 4)
            self.assertEqual(
                {template.template_case for template in templates}, set(TemplateCase)
            )
            self.assertTrue(
                all(template.status == TemplateStatus.ACTIVE for template in templates)
            )
            count = await session.scalar(
                select(func.count())
                .select_from(LetterPhrase)
                .where(LetterPhrase.user_id == user.id)
            )
            self.assertEqual(count, 14)

    async def test_generation_uses_exact_case_and_saves_metadata_atomically(self):
        async with self.sessions() as session:
            user = User(email="generation@example.test", password_hash="test")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            await DefaultTemplateProvisioner(session).ensure_for_user(user.id)
            project = Project(
                user_id=user.id,
                name="API",
                company_name="Example",
                technologies=["Python"],
                skills=[],
                achievements=[],
            )
            vacancy = AutoParsedJob(
                user_id=user.id,
                url="https://example.test/1",
                job_title="Python developer",
                job_text="Backend role",
                company_name="Acme",
            )
            session.add_all([project, vacancy])
            await session.commit()
            await session.refresh(vacancy)
            text_value = await TemplateGenerationService(session).generate(
                vacancy, user.id
            )
            self.assertIn("API", text_value)
            self.assertEqual(vacancy.cover_letter_template_case, "partial_match")
            self.assertIsNotNone(vacancy.cover_letter_template_id)
            self.assertTrue(vacancy.cover_letter_template_path)
            self.assertTrue(vacancy.is_generated)

    async def test_missing_exact_active_template_does_not_overwrite_old_letter(self):
        async with self.sessions() as session:
            user = User(email="missing@example.test", password_hash="test")
            session.add(user)
            await session.commit()
            await session.refresh(user)
            await DefaultTemplateProvisioner(session).ensure_for_user(user.id)
            template = await session.scalar(
                select(CoverLetterTemplate).where(
                    CoverLetterTemplate.user_id == user.id,
                    CoverLetterTemplate.template_case
                    == TemplateCase.NO_PORTFOLIO.value,
                )
            )
            template.status = "archived"
            vacancy = AutoParsedJob(
                user_id=user.id,
                url="https://example.test/2",
                job_title="Developer",
                job_text="Role",
                cover_letter_text="old letter",
            )
            session.add(vacancy)
            await session.commit()
            with self.assertRaisesRegex(
                TemplateConfigurationError, "active_template_not_found"
            ):
                await TemplateGenerationService(session).generate(vacancy, user.id)
            await session.refresh(vacancy)
            self.assertEqual(vacancy.cover_letter_text, "old letter")


if __name__ == "__main__":
    unittest.main()
