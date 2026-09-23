import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.parser import (
    DetailExtractionConfig,
    FieldRule,
    FieldSource,
    FormatUrlConfig,
    ListExtractionConfig,
    PaginationExtractionConfig,
    ParserWrite,
    RegexTransform,
    SelectorExtractionConfig,
    SelectorSource,
)
from app.schemas.parser_preview import PreviewRequest
from app.schemas.vacancy.single_vacancy import SingleVacancy
from app.schemas.vacancy.vacancy import Vacancy
from app.services.parser_preview import run_preview


def parser_payload():
    config = SelectorExtractionConfig(
        list=ListExtractionConfig(
            item_selector="article",
            fields={
                "title": FieldRule(source=SelectorSource(selectors=["h2"])),
                "link": FieldRule(
                    source=SelectorSource(
                        selectors=["a"],
                        extract="attribute",
                        attribute="href",
                        absolute_url=True,
                    )
                ),
                "vacancy_id": FieldRule(
                    source=FieldSource(field="link"),
                    transforms=[RegexTransform(pattern=r"/vacancy/(\d+)", group=1)],
                ),
            },
        ),
        detail=DetailExtractionConfig(
            fields={
                "job_title": FieldRule(source=SelectorSource(selectors=["h1"])),
                "job_text": FieldRule(source=SelectorSource(selectors=["main"])),
            }
        ),
        pagination=PaginationExtractionConfig(selectors=[".page"]),
    )
    return ParserWrite(
        name="test",
        base_url="https://jobs.test/search",
        single_url="https://jobs.test/vacancy/{vacancy_id}",
        has_pagination=True,
        evaluate_vacancy_list="legacy",
        evaluate_vacancy_page="legacy",
        evaluate_pagination="legacy",
        format_url=FormatUrlConfig(
            url_template="{base_url}", query_params={"text": "{text}", "page": "{page}"}
        ),
        extraction_engine="selectors_v1",
        fetch_mode="http",
        extraction_config=config,
    )


class FakeRuntime:
    def __init__(self):
        self.closed = False

    async def get_list(self, text, job_id):
        return [
            Vacancy(
                name=str(i), link=f"https://jobs.test/vacancy/{i}", vacancy_id=str(i)
            )
            for i in range(20)
        ]

    async def parse_single_by_url(self, url):
        return SingleVacancy(job_title="Title", job_text="Body", job_url=url)

    async def preview_pagination(self, text):
        return "https://jobs.test/search?page=0", 4

    async def aclose(self):
        self.closed = True


class PreviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_preview_is_limited_to_ten_and_closes_runtime(self):
        runtime = FakeRuntime()
        with (
            patch(
                "app.services.parser_preview.validate_public_url_async",
                new=AsyncMock(return_value="ok"),
            ),
            patch("app.services.parser_preview.create_runtime", return_value=runtime),
        ):
            response = await run_preview(
                PreviewRequest(
                    parser=parser_payload(), stage="list", search_text="python"
                )
            )
        self.assertEqual(len(response.result), 10)
        self.assertTrue(runtime.closed)

    async def test_detail_preview_rejects_other_hostname(self):
        with patch(
            "app.services.parser_preview.validate_public_url_async",
            new=AsyncMock(return_value="ok"),
        ):
            with self.assertRaises(ValueError):
                await run_preview(
                    PreviewRequest(
                        parser=parser_payload(),
                        stage="detail",
                        url="https://other.test/vacancy/1",
                    )
                )


if __name__ == "__main__":
    unittest.main()
