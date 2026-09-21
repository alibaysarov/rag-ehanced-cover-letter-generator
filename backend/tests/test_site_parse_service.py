import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from app.models import AutoParsedJob
from app.schemas.vacancy.single_vacancy import SingleVacancy
from app.schemas.vacancy.vacancy import Vacancy
from app.services.scraper.site_parse_service import SiteParseService


class SiteParseServiceTests(unittest.TestCase):
    def test_normalize_text_removes_blank_lines_and_extra_whitespace(self):
        self.assertEqual(
            "Сеньор Информационные технологии • PHP • Vue.js",
            SiteParseService._normalize_text(
                "\n\n  Сеньор\n\tИнформационные   технологии • PHP • Vue.js  \n"
            ),
        )


class SiteParseServiceCallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_saved_callback_is_awaited_after_vacancy_is_persisted(self):
        saved = AutoParsedJob(
            id=17,
            user_id=3,
            parsing_job_id=9,
            vacancy_id="external-17",
            url="https://example.test/vacancies/17",
            web_site="example.test",
            job_title="Python developer",
            job_text="Build backend services",
        )
        repository = AsyncMock()
        repository.save_vacancy.return_value = (saved, True)
        callback = AsyncMock()
        service = SiteParseService(repository, callback)

        page = AsyncMock()
        context = Mock()
        context.new_page = AsyncMock(return_value=page)
        parser = Mock()
        parser.parse_single_vacancy = AsyncMock(
            return_value=SingleVacancy(
                job_title="Python developer",
                job_text="Build backend services",
                job_url="https://example.test/vacancies/17",
            )
        )

        await service._process_vacancy(
            semaphore=asyncio.Semaphore(1),
            context=context,
            parser=parser,
            vacancy=Vacancy(
                name="Python developer",
                link="https://example.test/vacancies/17",
                vacancy_id="external-17",
            ),
            job_id=9,
            user_id=3,
            site_key="example.test",
        )

        callback.assert_awaited_once_with(saved)
        repository.record_vacancy_failure.assert_not_awaited()
        page.close.assert_awaited_once()


class SiteParseServiceLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_limit_applies_after_deduplication_and_before_detail_parsing(self):
        for limit, expected_ids in (
            (3, ["1", "2", "3"]),
            (10, ["1", "2", "3", "4", "5"]),
            (None, ["1", "2", "3", "4", "5"]),
        ):
            with self.subTest(limit=limit):
                repository = AsyncMock()
                service = SiteParseService(repository)
                service._process_vacancy = AsyncMock()
                parser = Mock()
                parser.get_list = AsyncMock(
                    return_value=[
                        Vacancy(
                            name="Python developer",
                            link=f"https://example.test/jobs/{vacancy_id}",
                            vacancy_id=vacancy_id,
                        )
                        for vacancy_id in ["1", "1", "2", "3", "4", "5"]
                    ]
                )
                browser = AsyncMock()
                await service.run(
                    job_id=9,
                    user_id=3,
                    site_key="example.test",
                    query="python",
                    parser=parser,
                    browser=browser,
                    vacancy_limit=limit,
                )
                self.assertEqual(
                    expected_ids,
                    [
                        call.kwargs["vacancy"].vacancy_id
                        for call in service._process_vacancy.await_args_list
                    ],
                )
                repository.record_found.assert_awaited_once_with(
                    9, "example.test", len(expected_ids)
                )
                repository.finish_site.assert_awaited_once_with(
                    9, "example.test", failed=False, error=None
                )
                browser.new_context.return_value.close.assert_awaited_once()

    async def test_empty_results_finish_successfully_with_zero_found(self):
        repository = AsyncMock()
        service = SiteParseService(repository)
        service._process_vacancy = AsyncMock()
        parser = Mock(get_list=AsyncMock(return_value=[]))
        await service.run(
            job_id=9,
            user_id=3,
            site_key="example.test",
            query="python",
            parser=parser,
            browser=AsyncMock(),
            vacancy_limit=3,
        )
        service._process_vacancy.assert_not_awaited()
        repository.record_found.assert_awaited_once_with(9, "example.test", 0)
        repository.finish_site.assert_awaited_once_with(
            9, "example.test", failed=False, error=None
        )


if __name__ == "__main__":
    unittest.main()
