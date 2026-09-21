import unittest
from urllib.parse import parse_qs, urlsplit

from pydantic import ValidationError

from app.schemas.parser import ParserSnapshot, ParserWrite, normalize_site_key
from app.services.scraper.parsers.configured import ConfiguredVacancyParser
from app.services.scraper.parsers.registry import create_parser


def snapshot(**overrides) -> ParserSnapshot:
    values = {
        "id": 1,
        "user_id": 2,
        "name": "Example",
        "site_key": "jobs.example.com",
        "base_url": "https://jobs.example.com/search?existing=kept",
        "single_url": "https://jobs.example.com/vacancy/{vacancy_id}",
        "has_pagination": True,
        "evaluate_vacancy_list": "() => []",
        "evaluate_vacancy_page": "() => ({job_title: 'x', job_text: 'y'})",
        "evaluate_pagination": "() => ['1']",
        "format_url": {
            "url_template": "{base_url}",
            "query_params": {"text": "{text}", "page": "{page}", "fixed": "true"},
        },
        "pagination_start": 1,
        "max_pages": 5,
        "version": 3,
    }
    values.update(overrides)
    return ParserSnapshot.model_validate(values)


class ConfiguredParserTests(unittest.TestCase):
    def test_registry_builds_only_from_snapshot(self):
        parser = create_parser(snapshot())
        self.assertIsInstance(parser, ConfiguredVacancyParser)
        self.assertEqual("Example", parser.get_name())
        self.assertEqual("jobs.example.com", parser.get_site_key())

    def test_format_url_preserves_and_encodes_parameters_once(self):
        parser = ConfiguredVacancyParser(snapshot())
        result = parser.format_url(
            "https://jobs.example.com/search?existing=kept",
            text="C++ & Python?",
            page=2,
        )
        query = parse_qs(urlsplit(result).query)
        self.assertEqual(["kept"], query["existing"])
        self.assertEqual(["C++ & Python?"], query["text"])
        self.assertEqual(["2"], query["page"])
        self.assertEqual(["true"], query["fixed"])
        self.assertNotIn("%252B", result)

    def test_format_url_omits_page_parameter_without_page_argument(self):
        parser = ConfiguredVacancyParser(snapshot())
        result = parser.format_url(parser.config.base_url, text="Python")
        self.assertNotIn("page", parse_qs(urlsplit(result).query))

    def test_single_url_encodes_non_numeric_id_as_component(self):
        parser = ConfiguredVacancyParser(snapshot())
        self.assertEqual(
            "https://jobs.example.com/vacancy/python%2Fsenior%3Fx%23y",
            parser.get_single_url("python/senior?x#y"),
        )

    def test_site_key_normalization_is_exact_hostname(self):
        self.assertEqual(
            "www.example.com", normalize_site_key("HTTPS://WWW.Example.COM/jobs")
        )

    def test_pagination_requires_script(self):
        values = snapshot().model_dump(
            exclude={"id", "user_id", "site_key", "version", "schema_version"}
        )
        values["evaluate_pagination"] = None
        with self.assertRaises(ValidationError):
            ParserWrite.model_validate(values)


if __name__ == "__main__":
    unittest.main()
