from app.services.scraper.parsers.geek_job import GeekJobVacancyParser
from app.services.scraper.parsers.general import GeneralVacancyParser
from app.services.scraper.parsers.hh import HHVacancyParser

PARSER_FACTORIES: dict[str, type[GeneralVacancyParser]] = {
    "hh.ru": HHVacancyParser,
    "geekjob.ru": GeekJobVacancyParser,
}


def get_parser_keys() -> tuple[str, ...]:
    return tuple(PARSER_FACTORIES.keys())


def create_parser(site_key: str) -> GeneralVacancyParser:
    try:
        parser_factory = PARSER_FACTORIES[site_key]
    except KeyError as exc:
        raise ValueError(f"Unknown parser site key: {site_key}") from exc

    return parser_factory()
