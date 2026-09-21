from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from app.schemas.parser import ParserSnapshot
from app.services.scraper.parsers.general import GeneralVacancyParser


class ConfiguredVacancyParser(GeneralVacancyParser):
    def __init__(self, config: ParserSnapshot):
        self.config = config
        super().__init__(
            config.name,
            config.base_url,
            config.has_pagination,
            site_key=config.site_key,
            pagination_start=config.pagination_start,
            max_pages=config.max_pages,
        )

    def get_single_url(self, vacancy_id) -> str:
        return self.config.single_url.replace(
            "{vacancy_id}", quote(str(vacancy_id), safe="")
        )

    def evaluate_pagination(self) -> str:
        if self.config.evaluate_pagination is None:
            raise ValueError(
                f"{self.get_name()}: evaluate_pagination is not configured"
            )
        return self.config.evaluate_pagination

    def evaluate_vacancy_list(self) -> str:
        return self.config.evaluate_vacancy_list

    def evaluate_vacancy_page(self) -> str:
        return self.config.evaluate_vacancy_page

    def format_url(self, url: str, **kwargs) -> str:
        text = str(kwargs.get("text", ""))
        page = kwargs.get("page")
        template = self.config.format_url.url_template
        values = {
            "base_url": url,
            "text": quote(text, safe=""),
            "page": quote(
                str(self.config.pagination_start if page is None else page), safe=""
            ),
        }
        rendered = template.format(**values)
        parts = urlsplit(rendered)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        for key, value in self.config.format_url.query_params.items():
            if page is None and "{page}" in value:
                continue
            query[key] = value.format(text=text, page=page)
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )
