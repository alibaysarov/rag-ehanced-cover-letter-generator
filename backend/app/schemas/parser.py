import re
import string
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_JS_SIZE = 64 * 1024
ALLOWED_TEMPLATE_FIELDS = {"base_url", "text", "page"}
FetchMode = Literal["http", "playwright"]
ExtractionEngine = Literal["legacy_js", "selectors_v1"]


def _validate_css(value: str) -> str:
    if not value.strip():
        raise ValueError("selector must not be blank")
    if len(value) > 1000:
        raise ValueError("selector is too long")
    try:
        BeautifulSoup("", "html.parser").select(value)
    except Exception as exc:
        raise ValueError("invalid CSS selector") from exc
    return value


class PlaywrightRequestConfig(BaseModel):
    wait_for_selector: str | None = Field(default=None, max_length=1000)
    wait_until: Literal["domcontentloaded", "load", "networkidle"] = "domcontentloaded"
    scroll_to_bottom: bool = False
    post_load_delay_ms: int = Field(default=0, ge=0, le=5000)

    @field_validator("wait_for_selector")
    @classmethod
    def valid_wait_selector(cls, value: str | None) -> str | None:
        return _validate_css(value) if value is not None else None


class RequestConfig(BaseModel):
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=20, ge=1, le=60)
    max_retries: int = Field(default=2, ge=0, le=3)
    retry_base_delay_seconds: float = Field(default=0.5, ge=0.1, le=5)
    playwright: PlaywrightRequestConfig = Field(default_factory=PlaywrightRequestConfig)

    @field_validator("headers")
    @classmethod
    def safe_headers(cls, value: dict[str, str]) -> dict[str, str]:
        forbidden = {"host", "content-length", "connection", "cookie", "authorization"}
        if len(value) > 20:
            raise ValueError("too many headers")
        for key, item in value.items():
            if (
                not key.strip()
                or not item.strip()
                or key.lower() in forbidden
                or key.lower().startswith("proxy-")
            ):
                raise ValueError("header is empty or forbidden")
        return value


class SelectorSource(BaseModel):
    kind: Literal["selector"] = "selector"
    selectors: list[str] = Field(min_length=1, max_length=5)
    extract: Literal["text", "attribute"] = "text"
    attribute: str | None = Field(default=None, max_length=128)
    absolute_url: bool = False

    @field_validator("selectors")
    @classmethod
    def valid_selectors(cls, value: list[str]) -> list[str]:
        return [_validate_css(item) for item in value]

    @model_validator(mode="after")
    def validate_attribute(self):
        if self.extract == "attribute" and not self.attribute:
            raise ValueError("attribute is required")
        if self.extract == "text" and self.attribute is not None:
            raise ValueError("attribute is only valid for attribute extraction")
        if self.absolute_url and self.attribute != "href":
            raise ValueError("absolute_url requires href attribute")
        return self


class FieldSource(BaseModel):
    kind: Literal["field"] = "field"
    field: str = Field(min_length=1, max_length=64)


class RegexTransform(BaseModel):
    kind: Literal["regex"] = "regex"
    pattern: str = Field(min_length=1, max_length=500)
    group: int = Field(default=0, ge=0)

    @field_validator("pattern")
    @classmethod
    def valid_regex(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError("invalid regex") from exc
        return value


class TextNormalize(BaseModel):
    strip: bool = True
    collapse_whitespace: bool = False


class FieldRule(BaseModel):
    source: SelectorSource | FieldSource
    required: bool = True
    normalize: TextNormalize = Field(default_factory=TextNormalize)
    transforms: list[RegexTransform] = Field(default_factory=list, max_length=5)


class ListExtractionConfig(BaseModel):
    item_selector: str
    fields: dict[str, FieldRule]

    @field_validator("item_selector")
    @classmethod
    def valid_item_selector(cls, value: str) -> str:
        return _validate_css(value)

    @model_validator(mode="after")
    def validate_fields(self):
        if set(self.fields) != {"title", "link", "vacancy_id"}:
            raise ValueError("list fields must be exactly title, link, vacancy_id")
        if any(
            not self.fields[name].required for name in ("title", "link", "vacancy_id")
        ):
            raise ValueError("list fields are required")
        source = self.fields["vacancy_id"].source
        if isinstance(source, FieldSource) and source.field != "link":
            raise ValueError("vacancy_id may reference only link")
        return self


class DetailExtractionConfig(BaseModel):
    fields: dict[str, FieldRule]

    @model_validator(mode="after")
    def validate_fields(self):
        if set(self.fields) not in (
            {"job_title", "job_text"},
            {"job_title", "job_text", "company_name"},
        ):
            raise ValueError("detail fields must contain job_title and job_text")
        for name in ("job_title", "job_text"):
            if not self.fields[name].required:
                raise ValueError(f"{name} is required")
        return self


class PaginationExtractionConfig(BaseModel):
    enabled: bool = True
    selectors: list[str] = Field(min_length=1, max_length=20)
    extract: Literal["text", "attribute"] = "text"
    attribute: str | None = Field(default=None, max_length=128)
    transforms: list[RegexTransform] = Field(default_factory=list, max_length=5)

    @field_validator("selectors")
    @classmethod
    def valid_selectors(cls, value: list[str]) -> list[str]:
        return [_validate_css(item) for item in value]


class SelectorExtractionConfig(BaseModel):
    schema_version: Literal[1] = 1
    list: ListExtractionConfig
    detail: DetailExtractionConfig
    pagination: PaginationExtractionConfig | None = None

    @model_validator(mode="after")
    def selector_limit(self):
        count = (
            len(self.list.fields["title"].source.selectors)
            if isinstance(self.list.fields["title"].source, SelectorSource)
            else 0
        )
        count += sum(
            len(rule.source.selectors)
            for rule in self.list.fields.values()
            if isinstance(rule.source, SelectorSource)
        )
        count += sum(
            len(rule.source.selectors)
            for rule in self.detail.fields.values()
            if isinstance(rule.source, SelectorSource)
        )
        if self.pagination:
            count += len(self.pagination.selectors)
        if count > 20:
            raise ValueError("too many selectors")
        return self


def normalize_site_key(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("credentials in URLs are not allowed")
    return parsed.hostname.lower().rstrip(".")


def template_fields(value: str) -> set[str]:
    try:
        return {
            field_name
            for _, field_name, _, _ in string.Formatter().parse(value)
            if field_name is not None
        }
    except ValueError as exc:
        raise ValueError("invalid template braces") from exc


class FormatUrlConfig(BaseModel):
    url_template: str = Field(min_length=1, max_length=4096)
    query_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("query_params")
    @classmethod
    def validate_query_params(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 100:
            raise ValueError("too many query parameters")
        for key, item in value.items():
            if not key.strip():
                raise ValueError("query parameter keys must not be empty")
            if not isinstance(item, str):
                raise ValueError("query parameter values must be strings")
            unknown = template_fields(item) - {"text", "page"}
            if unknown:
                raise ValueError(f"unknown placeholders: {', '.join(sorted(unknown))}")
        return value

    @field_validator("url_template")
    @classmethod
    def validate_url_template(cls, value: str) -> str:
        unknown = template_fields(value) - ALLOWED_TEMPLATE_FIELDS
        if unknown:
            raise ValueError(f"unknown placeholders: {', '.join(sorted(unknown))}")
        return value


class ParserWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    base_url: str = Field(min_length=1, max_length=4096)
    single_url: str = Field(min_length=1, max_length=4096)
    has_pagination: bool
    evaluate_vacancy_list: str = Field(min_length=1, max_length=MAX_JS_SIZE)
    evaluate_vacancy_page: str = Field(min_length=1, max_length=MAX_JS_SIZE)
    evaluate_pagination: str | None = Field(default=None, max_length=MAX_JS_SIZE)
    format_url: FormatUrlConfig
    pagination_start: int = Field(default=0, ge=0)
    max_pages: int = Field(default=5, ge=1, le=50)
    extraction_engine: ExtractionEngine = "legacy_js"
    fetch_mode: FetchMode = "playwright"
    request_config: RequestConfig = Field(default_factory=RequestConfig)
    extraction_config: SelectorExtractionConfig | None = None

    @field_validator("name", "evaluate_vacancy_list", "evaluate_vacancy_page")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_urls_and_pagination(self) -> "ParserWrite":
        site_key = normalize_site_key(self.base_url)
        if template_fields(self.single_url) != {"vacancy_id"}:
            raise ValueError("single_url must contain only {vacancy_id}")
        concrete_single = self.single_url.replace("{vacancy_id}", "sample")
        if normalize_site_key(concrete_single) != site_key:
            raise ValueError("single_url hostname must match base_url")
        rendered_search = self.format_url.url_template.replace(
            "{base_url}", self.base_url
        )
        rendered_search = rendered_search.replace("{text}", "sample").replace(
            "{page}", "0"
        )
        if normalize_site_key(rendered_search) != site_key:
            raise ValueError("search URL hostname must match base_url")
        uses_page = "page" in template_fields(self.format_url.url_template) or any(
            "page" in template_fields(value)
            for value in self.format_url.query_params.values()
        )
        if self.has_pagination and not (self.evaluate_pagination or "").strip():
            raise ValueError(
                "evaluate_pagination is required when pagination is enabled"
            )
        if self.has_pagination and not uses_page:
            raise ValueError("{page} is required when pagination is enabled")
        if self.extraction_engine == "legacy_js":
            if self.fetch_mode != "playwright":
                raise ValueError("legacy_js requires playwright")
            if self.extraction_config is not None:
                raise ValueError("legacy_js cannot have extraction_config")
        elif self.extraction_config is None:
            raise ValueError("selectors_v1 requires extraction_config")
        if self.extraction_config is not None:
            pagination = self.extraction_config.pagination
            if self.has_pagination and (pagination is None or not pagination.enabled):
                raise ValueError("enabled pagination requires pagination config")
            if (
                not self.has_pagination
                and pagination is not None
                and pagination.enabled
            ):
                raise ValueError("pagination config must be disabled")
        return self


class ParserCreate(ParserWrite):
    pass


class ParserUpdate(ParserWrite):
    version: int = Field(ge=1)


class ParserSnapshot(ParserWrite):
    model_config = ConfigDict(from_attributes=True)

    schema_version: int = 1
    id: int
    user_id: int
    site_key: str
    version: int


class ParserDetail(ParserWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_key: str
    version: int
    created_at: datetime
    updated_at: datetime
    is_in_use: bool = False
    can_delete: bool = True


class ParserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    site_key: str
    base_url: str
    has_pagination: bool
    version: int
    created_at: datetime
    updated_at: datetime
    is_in_use: bool
    can_delete: bool


class ParserList(BaseModel):
    items: list[ParserListItem]
    total: int
    page: int
    page_size: int
