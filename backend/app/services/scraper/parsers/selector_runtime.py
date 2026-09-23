import asyncio
from urllib.parse import urlencode

from app.schemas.parser import ParserSnapshot
from app.schemas.vacancy.single_vacancy import SingleVacancy
from app.schemas.vacancy.vacancy import Vacancy
from app.services.scraper.extraction.selectors import (
    ExtractionError,
    extract_detail,
    extract_list,
    extract_pagination,
)
from app.services.scraper.fetchers import PageFetcher

MAX_CONCURRENT_LIST_REQUESTS = 5


class SelectorParserRuntime:
    def __init__(self, snapshot: ParserSnapshot, fetcher: PageFetcher):
        if snapshot.extraction_config is None:
            raise ValueError("selector runtime requires extraction_config")
        self.snapshot = snapshot
        self.fetcher = fetcher
        self.config = snapshot.extraction_config
        self._list_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LIST_REQUESTS)

    def _url(
        self, *, text: str = "", page: int = 0, vacancy_id: str | None = None
    ) -> str:
        if vacancy_id is not None:
            return self.snapshot.single_url.replace("{vacancy_id}", vacancy_id)
        template = self.snapshot.format_url.url_template.replace(
            "{base_url}", self.snapshot.base_url
        )
        template = template.replace("{text}", text).replace("{page}", str(page))
        params = {
            key: value.replace("{text}", text).replace("{page}", str(page))
            for key, value in self.snapshot.format_url.query_params.items()
        }
        return f"{template}?{urlencode(params)}" if params else template

    async def _fetch_list(self, text: str, page: int) -> tuple[list[Vacancy], str, str]:
        async with self._list_semaphore:
            fetched = await self.fetcher.fetch(self._url(text=text, page=page))
        return (
            extract_list(fetched.html, fetched.url, self.config.list),
            fetched.html,
            fetched.url,
        )

    async def get_list(self, text: str, job_id: int) -> list[Vacancy]:
        try:
            first, first_html, _ = await self._fetch_list(
                text, self.snapshot.pagination_start
            )
        except ExtractionError:
            raise
        except Exception as exc:
            raise RuntimeError(f"list fetch failed: {exc}") from exc
        if not self.snapshot.has_pagination or self.config.pagination is None:
            return first
        try:
            pages = extract_pagination(
                first_html, self.config.pagination, self.snapshot.max_pages
            )
        except ExtractionError:
            raise
        except Exception as exc:
            raise RuntimeError(f"pagination extraction failed: {exc}") from exc
        page_numbers = range(
            self.snapshot.pagination_start + 1, self.snapshot.pagination_start + pages
        )
        try:
            rest = await asyncio.gather(
                *(self._fetch_list(text, page) for page in page_numbers)
            )
        except ExtractionError:
            raise
        except Exception as exc:
            raise RuntimeError(f"pagination page fetch failed: {exc}") from exc
        return [item for page_items, _, _ in rest for item in page_items] + first

    async def parse_single_vacancy(self, vacancy_id: str) -> SingleVacancy:
        return await self.parse_single_by_url(self._url(vacancy_id=vacancy_id))

    async def parse_single_by_url(self, url: str) -> SingleVacancy:
        fetched = await self.fetcher.fetch(url)
        return extract_detail(fetched.html, fetched.url, self.config.detail)

    async def preview_pagination(self, text: str) -> tuple[str, int]:
        fetched = await self.fetcher.fetch(
            self._url(text=text, page=self.snapshot.pagination_start)
        )
        if self.config.pagination is None:
            return fetched.url, 1
        return fetched.url, extract_pagination(
            fetched.html, self.config.pagination, self.snapshot.max_pages
        )

    async def aclose(self) -> None:
        await self.fetcher.aclose()
