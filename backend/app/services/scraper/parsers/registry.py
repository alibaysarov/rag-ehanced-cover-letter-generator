from app.schemas.parser import ParserSnapshot
from app.services.scraper.parsers.configured import ConfiguredVacancyParser
from app.services.scraper.parsers.general import GeneralVacancyParser


def create_parser(snapshot: ParserSnapshot | dict) -> GeneralVacancyParser:
    return ConfiguredVacancyParser(ParserSnapshot.model_validate(snapshot))
