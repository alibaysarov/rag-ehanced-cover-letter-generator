import unittest

from app.services.scraper.parsers.geek_job import GeekJobVacancyParser
from app.services.scraper.parsers.hh import HHVacancyParser
from app.services.scraper.parsers.registry import create_parser, get_parser_keys
from app.services.scraper.vacancy_scraper import VacancyScrapingService


class ParserRegistryTests(unittest.TestCase):
    def test_parser_keys_are_explicit_site_domains(self):
        self.assertEqual(("hh.ru", "geekjob.ru"), get_parser_keys())

    def test_create_parser_returns_hh_parser(self):
        parser = create_parser("hh.ru")

        self.assertIsInstance(parser, HHVacancyParser)
        self.assertEqual("hh.ru", parser.get_name())

    def test_create_parser_returns_geekjob_parser(self):
        parser = create_parser("geekjob.ru")

        self.assertIsInstance(parser, GeekJobVacancyParser)
        self.assertEqual("geekjob.ru", parser.get_name())

    def test_create_parser_rejects_unknown_key(self):
        with self.assertRaisesRegex(ValueError, "Unknown parser site key"):
            create_parser("unknown.example")

    def test_vacancy_scraper_uses_registry_for_known_urls(self):
        service = VacancyScrapingService()

        self.assertIsInstance(
            service.get_parser("https://hh.ru/vacancy/123"), HHVacancyParser
        )
        self.assertIsInstance(
            service.get_parser("https://geekjob.ru/vacancy/python-developer"),
            GeekJobVacancyParser,
        )
        self.assertIsNone(service.get_parser("https://example.com/vacancy/1"))


if __name__ == "__main__":
    unittest.main()
