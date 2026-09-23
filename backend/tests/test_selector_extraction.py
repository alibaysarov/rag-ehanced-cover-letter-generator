import unittest

from app.schemas.parser import (
    DetailExtractionConfig,
    FieldRule,
    FieldSource,
    ListExtractionConfig,
    PaginationExtractionConfig,
    RegexTransform,
    SelectorSource,
    TextNormalize,
)
from app.services.scraper.extraction.selectors import (
    ExtractionError,
    extract_detail,
    extract_list,
    extract_pagination,
)


def selector(
    selectors, *, extract="text", attribute=None, absolute_url=False, transforms=None
):
    return FieldRule(
        source=SelectorSource(
            selectors=selectors,
            extract=extract,
            attribute=attribute,
            absolute_url=absolute_url,
        ),
        normalize=TextNormalize(collapse_whitespace=True),
        transforms=transforms or [],
    )


class SelectorExtractionTests(unittest.TestCase):
    def setUp(self):
        self.list_config = ListExtractionConfig(
            item_selector="article.card",
            fields={
                "title": selector(["h2", ".fallback-title"]),
                "link": selector(
                    ["a.primary", "a"],
                    extract="attribute",
                    attribute="href",
                    absolute_url=True,
                ),
                "vacancy_id": FieldRule(
                    source=FieldSource(field="link"),
                    transforms=[RegexTransform(pattern=r"/vacancy/(\d+)", group=1)],
                ),
            },
        )

    def test_list_uses_fallback_and_resolves_relative_link(self):
        html = """
        <article class='card'><h2>  Python   Developer </h2><a href='/vacancy/42'>open</a></article>
        <article class='card'><span class='fallback-title'>Fallback title</span><a class='primary' href='https://jobs.test/vacancy/7'>open</a></article>
        """
        result = extract_list(html, "https://jobs.test/search", self.list_config)
        self.assertEqual([item.vacancy_id for item in result], ["42", "7"])
        self.assertEqual(result[0].link, "https://jobs.test/vacancy/42")
        self.assertEqual(result[0].name, "Python Developer")

    def test_invalid_cards_are_skipped_and_empty_result_fails(self):
        with self.assertRaises(ExtractionError) as error:
            extract_list(
                "<article class='card'><h2>Missing link</h2></article>",
                "https://jobs.test",
                self.list_config,
            )
        self.assertEqual(error.exception.code, "no_valid_items")

    def test_detail_extracts_required_and_optional_fields(self):
        config = DetailExtractionConfig(
            fields={
                "job_title": selector(["h1"]),
                "job_text": selector([".missing", "article"]),
                "company_name": selector([".company"]),
            }
        )
        result = extract_detail(
            "<h1>Title</h1><article>  Long\n description </article><span class='company'>Acme</span>",
            "https://jobs.test/vacancy/1",
            config,
        )
        self.assertEqual(result.job_title, "Title")
        self.assertEqual(result.job_text, "Long description")
        self.assertEqual(result.company_name, "Acme")

    def test_pagination_deduplicates_and_limits(self):
        config = PaginationExtractionConfig(
            selectors=[".page"], transforms=[RegexTransform(pattern=r"(\d+)", group=1)]
        )
        self.assertEqual(
            extract_pagination(
                "<a class='page'>2</a><a class='page'>5</a><a class='page'>5</a>",
                config,
                3,
            ),
            3,
        )


if __name__ == "__main__":
    unittest.main()
