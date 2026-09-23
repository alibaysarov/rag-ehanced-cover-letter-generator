import asyncio
import random

from playwright.async_api import Browser

from app.helper import scroll_page_bottom, secure_request_route
from app.schemas.parser import RequestConfig
from app.services.scraper.security import validate_public_url_async

from . import FetchedPage


class PlaywrightPageFetcher:
    def __init__(self, browser: Browser, config: RequestConfig):
        self.browser = browser
        self.config = config
        self.context = None

    async def fetch(self, url: str) -> FetchedPage:
        await validate_public_url_async(url)
        if self.context is None:
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                extra_http_headers=self.config.headers,
            )
        for attempt in range(self.config.max_retries + 1):
            page = await self.context.new_page()
            try:
                await page.route("**/*", secure_request_route)
                options = self.config.playwright
                await page.goto(
                    url,
                    wait_until=options.wait_until,
                    timeout=self.config.timeout_seconds * 1000,
                )
                if options.wait_for_selector:
                    await page.wait_for_selector(
                        options.wait_for_selector,
                        timeout=self.config.timeout_seconds * 1000,
                    )
                if options.scroll_to_bottom:
                    await scroll_page_bottom(page)
                if options.post_load_delay_ms:
                    await page.wait_for_timeout(options.post_load_delay_ms)
                return FetchedPage(
                    await validate_public_url_async(page.url), await page.content()
                )
            except Exception as exc:
                if attempt >= self.config.max_retries:
                    raise exc
                await asyncio.sleep(
                    min(
                        5,
                        self.config.retry_base_delay_seconds * (2**attempt)
                        + random.uniform(0, 0.25),
                    )
                )
            finally:
                await page.close()
        raise RuntimeError("unreachable")

    async def aclose(self) -> None:
        if self.context is not None:
            await self.context.close()
