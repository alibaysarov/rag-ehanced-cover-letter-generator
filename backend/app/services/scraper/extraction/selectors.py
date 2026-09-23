"""Pure BeautifulSoup extraction for selector-based parsers."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.schemas.parser import (
    DetailExtractionConfig,
    FieldRule,
    FieldSource,
    ListExtractionConfig,
    PaginationExtractionConfig,
)
from app.schemas.vacancy.single_vacancy import SingleVacancy
from app.schemas.vacancy.vacancy import Vacancy

MAX_RESULT_CARDS = 2000


class ExtractionError(ValueError):
    def __init__(self, stage: str, code: str, message: str):
        self.stage = stage
        self.code = code
        super().__init__(f"{stage}: {message}")


def _normalize(value: str, rule: FieldRule) -> str:
    if rule.normalize.strip:
        value = value.strip()
    if rule.normalize.collapse_whitespace:
        value = " ".join(value.split())
    for transform in rule.transforms:
        match = re.search(transform.pattern, value)
        if not match:
            return ""
        try:
            value = match.group(transform.group)
        except IndexError:
            return ""
    return value.strip() if rule.normalize.strip else value


def _extract(
    node: Tag | BeautifulSoup, rule: FieldRule, page_url: str, fields: dict[str, str]
) -> str:
    source = rule.source
    if isinstance(source, FieldSource):
        return _normalize(fields.get(source.field, ""), rule)
    for selector in source.selectors:
        element = node.select_one(selector)
        if element is None:
            continue
        if source.extract == "attribute":
            value = element.get(source.attribute or "", "")
        else:
            value = element.get_text(" ", strip=False)
        value = _normalize(str(value), rule)
        if value:
            if source.absolute_url:
                value = urljoin(page_url, value)
            return value
    return ""


def extract_list(
    html: str, page_url: str, config: ListExtractionConfig
) -> list[Vacancy]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(config.item_selector)
    if not cards:
        raise ExtractionError("list", "items_not_found", "no vacancy cards found")
    result: list[Vacancy] = []
    skipped = 0
    for card in cards[:MAX_RESULT_CARDS]:
        fields: dict[str, str] = {}
        for name in ("title", "link", "vacancy_id"):
            fields[name] = _extract(card, config.fields[name], page_url, fields)
        if all(fields[name] for name in ("title", "link", "vacancy_id")):
            result.append(
                Vacancy(
                    name=fields["title"],
                    link=fields["link"],
                    vacancy_id=fields["vacancy_id"],
                )
            )
        else:
            skipped += 1
    if not result:
        raise ExtractionError(
            "list", "no_valid_items", f"no valid cards ({skipped} skipped)"
        )
    return result


def extract_detail(
    html: str, page_url: str, config: DetailExtractionConfig
) -> SingleVacancy:
    soup = BeautifulSoup(html, "html.parser")
    fields = {
        name: _extract(soup, rule, page_url, {}) for name, rule in config.fields.items()
    }
    if not fields.get("job_title") or not fields.get("job_text"):
        raise ExtractionError(
            "detail", "required_field_missing", "job_title or job_text is empty"
        )
    return SingleVacancy(
        job_title=fields["job_title"],
        job_text=fields["job_text"],
        job_url=page_url,
        company_name=fields.get("company_name") or None,
    )


def extract_pagination(
    html: str, config: PaginationExtractionConfig, max_pages: int
) -> int:
    if not config.enabled:
        return 1
    soup = BeautifulSoup(html, "html.parser")
    numbers: set[int] = set()
    for selector in config.selectors:
        for element in soup.select(selector):
            raw_value = (
                element.get(config.attribute or "", "")
                if config.extract == "attribute"
                else element.get_text(" ", strip=True)
            )
            value = str(raw_value) if raw_value is not None else ""
            for transform in config.transforms or []:
                match = re.search(transform.pattern, value)
                value = (
                    match.group(transform.group)
                    if match and transform.group <= (match.lastindex or 0)
                    else (match.group(0) if match else "")
                )
            try:
                number = int(value.strip())
            except ValueError:
                continue
            if number > 0:
                numbers.add(number)
    return min(max(numbers), max_pages) if numbers else 1
