import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pydantic import ValidationError

from app.models import Parser, ParsingJob, User
from app.repository.parsing_job_repository import ParsingJobRepository
from app.schemas.api.auto_parse import StartParseRequest
from app.schemas.generation_mode import GenerationMode


class VacancyLimitRequestTests(unittest.TestCase):
    def test_omitted_limit_preserves_unlimited_search(self):
        self.assertIsNone(StartParseRequest(query="python").vacancy_limit)

    def test_limit_requires_an_integer_between_one_and_one_thousand(self):
        for value in (0, -1, 1.5, True, "10", 1001):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                StartParseRequest.model_validate(
                    {"query": "python", "vacancy_limit": value}
                )
        for value in (1, 10, 1000):
            self.assertEqual(
                value,
                StartParseRequest(query="python", vacancy_limit=value).vacancy_limit,
            )


class VacancyLimitAllocationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.parsers = [
            Parser(
                id=index,
                user_id=7,
                name=f"Site {index}",
                site_key=f"site{index}.test",
                base_url=f"https://site{index}.test/search",
                single_url=f"https://site{index}.test/jobs/{{vacancy_id}}",
                has_pagination=False,
                evaluate_vacancy_list="() => []",
                evaluate_vacancy_page="() => ({})",
                format_url={
                    "url_template": "{base_url}",
                    "query_params": {"text": "{text}"},
                },
            )
            for index in range(1, 5)
        ]
        self.session = AsyncMock()
        self.session.begin = Mock(return_value=AsyncMock())
        self.session.scalar.return_value = User(
            id=7, email="limits@example.test", password_hash="x"
        )
        self.session.scalars.return_value = SimpleNamespace(all=lambda: self.parsers)

        def add(record):
            record.id = 100 + self.session.add.call_count

        self.session.add = Mock(side_effect=add)
        context = AsyncMock()
        context.__aenter__.return_value = self.session
        self.repository = ParsingJobRepository(lambda: context)

    async def test_ten_vacancies_are_distributed_as_three_three_three_one(self):
        job, sites = await self.repository.create_job_with_parsers(
            7, "python", GenerationMode.TEMPLATE, vacancy_limit=10
        )
        self.assertEqual([3, 3, 3, 1], [site.vacancy_limit for site in sites])
        self.assertEqual(GenerationMode.TEMPLATE, job.generation_mode)
        self.assertTrue(all(site.parsing_job_id == job.id for site in sites))
        self.assertEqual(
            [parser.site_key for parser in self.parsers],
            [site.site_key for site in sites],
        )

    async def test_small_and_uneven_budgets_create_only_positive_site_quotas(self):
        for limit, expected in (
            (1, [1]),
            (2, [1, 1]),
            (4, [1, 1, 1, 1]),
            (5, [2, 2, 1]),
            (8, [2, 2, 2, 2]),
            (1000, [250, 250, 250, 250]),
        ):
            with self.subTest(limit=limit):
                _, sites = await self.repository.create_job_with_parsers(
                    7, "python", vacancy_limit=limit
                )
                self.assertEqual(expected, [site.vacancy_limit for site in sites])

    async def test_omitted_limit_includes_every_parser_without_a_quota(self):
        _, sites = await self.repository.create_job_with_parsers(7, "python")
        self.assertEqual([None] * 4, [site.vacancy_limit for site in sites])

    async def test_empty_catalog_still_rejects_search(self):
        self.parsers.clear()
        with self.assertRaisesRegex(ValueError, "parsers_empty"):
            await self.repository.create_job_with_parsers(7, "python", vacancy_limit=10)

    async def test_single_site_receives_the_entire_budget(self):
        self.parsers = self.parsers[:1]
        _, sites = await self.repository.create_job_with_parsers(
            7, "python", vacancy_limit=10
        )
        self.assertEqual([10], [site.vacancy_limit for site in sites])


class VacancyLimitEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_passes_the_limit_to_persisted_site_jobs(self):
        from app.api.v1.endpoints.auto_parse_router import start_parse_test

        with (
            patch(
                "app.api.v1.endpoints.auto_parse_router.ParsingJobRepository"
            ) as repository_class,
            patch(
                "app.api.v1.endpoints.auto_parse_router.run_in_threadpool",
                new_callable=AsyncMock,
            ) as dispatch,
        ):
            repository = repository_class.return_value
            repository.create_job_with_parsers = AsyncMock(
                return_value=(
                    ParsingJob(id=9, user_id=7, query="python"),
                    [SimpleNamespace(id=11), SimpleNamespace(id=12)],
                )
            )
            result = await start_parse_test(
                user=User(id=7, email="limits@example.test", password_hash="x"),
                body=StartParseRequest(
                    query="python",
                    generation_mode=GenerationMode.TEMPLATE,
                    vacancy_limit=10,
                ),
            )
        self.assertEqual({"parsing_job_id": 9}, result)
        repository.create_job_with_parsers.assert_awaited_once_with(
            7, "python", GenerationMode.TEMPLATE, vacancy_limit=10
        )
        self.assertEqual(2, dispatch.await_count)


if __name__ == "__main__":
    unittest.main()
