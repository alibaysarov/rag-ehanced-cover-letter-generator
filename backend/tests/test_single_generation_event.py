import json
import unittest
from unittest.mock import AsyncMock, patch

from app.models import AutoParsedJob
from app.schemas.generation_mode import GenerationMode
from app.tasks.listener.single_generation_listener import handle_event
from app.tasks.single_generation import build_generated_event


class GeneratedVacancyEventTests(unittest.TestCase):
    def test_template_event_contains_complete_ready_vacancy(self):
        vacancy = AutoParsedJob(
            id=17,
            user_id=3,
            parsing_job_id=9,
            vacancy_id="external-17",
            url="https://example.test/vacancies/17",
            web_site="example.test",
            job_title="Python developer",
            job_text="Build backend services",
            is_generated=True,
            cover_letter_text="Ready letter",
        )

        event = build_generated_event(
            user_id=3,
            batch_id=9,
            vacancy_id=17,
            cover_letter_text="Ready letter",
            mode=GenerationMode.TEMPLATE,
            vacancy=vacancy,
        )

        self.assertEqual("generation.vacancy_ready", event["type"])
        self.assertEqual("template", event["generation_mode"])
        self.assertEqual(9, event["parsing_job_id"])
        self.assertTrue(event["vacancy"]["is_generated"])
        self.assertEqual("Ready letter", event["vacancy"]["cover_letter_text"])

    def test_ai_event_keeps_legacy_payload(self):
        event = build_generated_event(
            user_id=3,
            batch_id=9,
            vacancy_id=17,
            cover_letter_text="AI letter",
            mode=GenerationMode.AI,
        )

        self.assertNotIn("type", event)
        self.assertEqual(17, event["vacancy_id"])
        self.assertEqual("AI letter", event["cover_letter_text"])


class CoverLetterWebSocketListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_listener_forwards_ready_event_without_mutating_source(self):
        event = {
            "type": "generation.vacancy_ready",
            "user_id": 3,
            "batch_id": 9,
            "parsing_job_id": 9,
            "status": "generated",
            "generation_mode": "template",
            "vacancy": {"id": 17, "is_generated": True},
        }
        original = dict(event)
        websocket_manager = AsyncMock()

        with patch(
            "app.tasks.listener.single_generation_listener.ws_manager",
            websocket_manager,
        ):
            await handle_event(event)

        self.assertEqual(original, event)
        websocket_manager.send_text.assert_awaited_once_with(
            "3",
            json.dumps(
                {key: value for key, value in event.items() if key != "user_id"}
            ),
        )


if __name__ == "__main__":
    unittest.main()
