import unittest

from app.services.scraper.site_parse_service import SiteParseService


class SiteParseServiceTests(unittest.TestCase):
    def test_normalize_text_removes_blank_lines_and_extra_whitespace(self):
        self.assertEqual(
            "Сеньор Информационные технологии • PHP • Vue.js",
            SiteParseService._normalize_text(
                "\n\n  Сеньор\n\tИнформационные   технологии • PHP • Vue.js  \n"
            ),
        )


if __name__ == "__main__":
    unittest.main()
