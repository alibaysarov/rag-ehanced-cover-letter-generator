import asyncio
import random
from email.utils import parsedate_to_datetime
from time import time

import httpx

from app.schemas.parser import RequestConfig
from app.services.scraper.security import validate_public_url_async

from . import FetchedPage

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
RETRY_STATUSES = {408, 429, 500, 502, 503, 504}
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "User-Agent": "CoverLetterParser/1.0",
}


class HttpxPageFetcher:
    def __init__(self, config: RequestConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=config.timeout_seconds,
            headers={**DEFAULT_HEADERS, **config.headers},
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )

    async def fetch(self, url: str) -> FetchedPage:
        await validate_public_url_async(url)
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self.client.get(url)
                retryable = response.status_code in RETRY_STATUSES
                if response.status_code >= 400 and not retryable:
                    response.raise_for_status()
                if retryable and attempt < self.config.max_retries:
                    await self._backoff(attempt, response)
                    continue
                response.raise_for_status()
                await validate_public_url_async(str(response.url))
                if len(response.content) > MAX_RESPONSE_BYTES:
                    raise ValueError("response body is too large")
                content_type = (
                    response.headers.get("content-type", "").split(";", 1)[0].lower()
                )
                if content_type not in {"text/html", "application/xhtml+xml", ""}:
                    raise ValueError("response is not HTML")
                return FetchedPage(str(response.url), response.text)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt >= self.config.max_retries:
                    raise
                await self._backoff(attempt, None)
        raise RuntimeError("unreachable")

    async def _backoff(self, attempt: int, response: httpx.Response | None) -> None:
        delay = min(
            5.0,
            self.config.retry_base_delay_seconds * (2**attempt)
            + random.uniform(0, 0.25),
        )
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    delay = min(10.0, max(delay, float(retry_after)))
                except ValueError:
                    try:
                        delay = min(
                            10.0,
                            max(
                                delay,
                                parsedate_to_datetime(retry_after).timestamp() - time(),
                            ),
                        )
                    except (TypeError, ValueError, OverflowError):
                        pass
        await asyncio.sleep(delay)

    async def aclose(self) -> None:
        await self.client.aclose()
