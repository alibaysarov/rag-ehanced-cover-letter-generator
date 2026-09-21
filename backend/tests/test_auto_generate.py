import unittest
from unittest.mock import AsyncMock, patch

from app.models import AutoParsedJob
from app.schemas.generation_mode import GenerationMode
from app.services.auto_generate import (
    maybe_start_template_generation_for_vacancy,
    start_single_template_generation,
)


class PerVacancyTemplateGenerationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.vacancy = AutoParsedJob(
            id=17,
            user_id=3,
            parsing_job_id=9,
            vacancy_id="external-17",
            url="https://example.test/vacancies/17",
            web_site="example.test",
            job_title="Python developer",
            job_text="Build backend services",
        )
        self.repository = AsyncMock()

    @patch("app.services.auto_generate.start_single_template_generation")
    async def test_template_mode_dispatches_immediately_after_one_vacancy(
        self, start_single
    ):
        started = await maybe_start_template_generation_for_vacancy(
            self.vacancy,
            GenerationMode.TEMPLATE,
            self.repository,
        )

        self.assertTrue(started)
        start_single.assert_called_once_with(3, 9, 17)
        self.repository.record_template_generation_started.assert_awaited_once_with(9)
        self.repository.set_auto_generation_error.assert_not_awaited()

    @patch("app.services.auto_generate.start_single_template_generation")
    async def test_ai_mode_does_not_dispatch_automatic_generation(self, start_single):
        started = await maybe_start_template_generation_for_vacancy(
            self.vacancy,
            GenerationMode.AI,
            self.repository,
        )

        self.assertFalse(started)
        start_single.assert_not_called()
        self.repository.record_template_generation_started.assert_not_awaited()

    @patch(
        "app.services.auto_generate.start_single_template_generation",
        side_effect=RuntimeError("broker unavailable"),
    )
    async def test_dispatch_error_is_recorded(self, start_single):
        with self.assertRaisesRegex(RuntimeError, "broker unavailable"):
            await maybe_start_template_generation_for_vacancy(
                self.vacancy,
                GenerationMode.TEMPLATE,
                self.repository,
            )

        start_single.assert_called_once_with(3, 9, 17)
        self.repository.record_template_generation_started.assert_not_awaited()
        self.repository.set_auto_generation_error.assert_awaited_once_with(
            9, "broker unavailable"
        )

    def test_single_dispatch_tracks_dynamic_batch_total_and_uses_template_mode(self):
        with (
            patch("app.services.auto_generate.sync_client") as redis,
            patch("app.tasks.single_generation.delay") as delay,
        ):
            start_single_template_generation(3, 9, 17)

        redis.hincrby.assert_called_once_with("batch_meta:9", "total", 1)
        redis.expire.assert_called_once_with("batch_meta:9", 3600)
        delay.assert_called_once_with(
            3,
            17,
            "",
            "",
            9,
            generation_mode="template",
        )


if __name__ == "__main__":
    unittest.main()
