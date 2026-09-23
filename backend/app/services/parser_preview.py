import time
from contextlib import asynccontextmanager
from typing import cast
from urllib.parse import urlencode, urlparse

from app.decorators.browser import pw_browser
from app.schemas.parser import ParserSnapshot
from app.schemas.parser_preview import PreviewRequest, PreviewResponse
from app.services.scraper.parsers.runtime_registry import create_runtime
from app.services.scraper.parsers.selector_runtime import SelectorParserRuntime
from app.services.scraper.security import validate_public_url_async


@asynccontextmanager
async def _preview_browser(fetch_mode: str):
    if fetch_mode == "playwright":
        async with pw_browser(headless=True) as browser:
            yield browser
    else:
        yield None


async def run_preview(payload: PreviewRequest) -> PreviewResponse:
    parser = payload.parser
    if parser.extraction_engine != "selectors_v1":
        raise ValueError("preview is available only for selectors_v1")
    await validate_public_url_async(parser.base_url)
    snapshot = ParserSnapshot.model_validate(
        {
            **parser.model_dump(mode="python"),
            "id": 0,
            "user_id": 0,
            "site_key": urlparse(parser.base_url).hostname,
            "version": 1,
        }
    )
    start = time.perf_counter()
    async with _preview_browser(parser.fetch_mode) as browser:
        runtime = cast(SelectorParserRuntime, create_runtime(snapshot, browser))
        try:
            if payload.stage == "detail":
                assert payload.url is not None
                await validate_public_url_async(payload.url)
                if urlparse(payload.url).hostname != urlparse(parser.base_url).hostname:
                    raise ValueError("preview URL hostname must match base_url")
                item = await runtime.parse_single_by_url(payload.url)
                result = item.model_dump()
                resolved_url = item.job_url or payload.url
            elif payload.stage == "pagination":
                resolved_url, count = await runtime.preview_pagination(
                    payload.search_text
                )
                result = count
            else:
                items = await runtime.get_list(payload.search_text, 0)
                result = [item.model_dump() for item in items[:10]]
                template = (
                    parser.format_url.url_template.replace(
                        "{base_url}", parser.base_url
                    )
                    .replace("{text}", payload.search_text)
                    .replace("{page}", str(payload.page))
                )
                params = {
                    key: value.replace("{text}", payload.search_text).replace(
                        "{page}", str(payload.page)
                    )
                    for key, value in parser.format_url.query_params.items()
                }
                resolved_url = f"{template}?{urlencode(params)}" if params else template
            return PreviewResponse(
                resolved_url=resolved_url,
                fetch_mode=parser.fetch_mode,
                stage=payload.stage,
                result=result,
                warnings=[],
                timing_ms=max(0, int((time.perf_counter() - start) * 1000)),
            )
        finally:
            await runtime.aclose()
