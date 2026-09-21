import string
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_JS_SIZE = 64 * 1024
ALLOWED_TEMPLATE_FIELDS = {"base_url", "text", "page"}


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
