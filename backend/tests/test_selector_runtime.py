import asyncio
import unittest
from unittest.mock import AsyncMock

from app.schemas.parser import (
    DetailExtractionConfig,
    FieldRule,
    FieldSource,
    FormatUrlConfig,
    ListExtractionConfig,
    PaginationExtractionConfig,
    ParserSnapshot,
    RegexTransform,
    SelectorExtractionConfig,
    SelectorSource,
)
from app.services.scraper.extraction.selectors import ExtractionError
from app.services.scraper.fetchers import FetchedPage
from app.services.scraper.parsers.selector_runtime import SelectorParserRuntime


def text_rule(selector):
    return FieldRule(source=SelectorSource(selectors=[selector]))


def snapshot():
    config = SelectorExtractionConfig(
        list=ListExtractionConfig(
            item_selector="article",
            fields={
                "title": text_rule("h2"),
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
            fields={"job_title": text_rule("h1"), "job_text": text_rule("main")}
        ),
        pagination=PaginationExtractionConfig(selectors=[".page"]),
    )
    return ParserSnapshot(
        id=1,
        user_id=1,
        site_key="jobs.test",
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
        version=1,
    )


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.closed = False

    async def fetch(self, url):
        self.calls.append(url)
        await asyncio.sleep(0)
        if url.endswith("page=1"):
            return FetchedPage(
                url, "<article><h2>Two</h2><a href='/vacancy/2'>x</a></article>"
            )
        return FetchedPage(
            url,
            "<a class='page'>2</a><article><h2>One</h2><a href='/vacancy/1'>x</a></article>",
        )

    async def aclose(self):
        self.closed = True


class SelectorRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_pagination_fetches_additional_pages(self):
        fetcher = FakeFetcher(None)
        runtime = SelectorParserRuntime(snapshot(), fetcher)
        result = await runtime.get_list("python", 1)
        self.assertEqual([item.vacancy_id for item in result], ["2", "1"])
        self.assertEqual(len(fetcher.calls), 2)

    async def test_list_extraction_error_is_not_retried_or_hidden(self):
        fetcher = AsyncMock()
        fetcher.fetch.return_value = FetchedPage(
            "https://jobs.test/search", "<html></html>"
        )
        runtime = SelectorParserRuntime(snapshot(), fetcher)
        with self.assertRaises(ExtractionError) as error:
            await runtime.get_list("python", 1)
        self.assertEqual(error.exception.code, "items_not_found")
        fetcher.fetch.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
