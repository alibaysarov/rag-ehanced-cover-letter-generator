from contextlib import asynccontextmanager
from playwright.async_api import async_playwright


@asynccontextmanager
async def pw_browser(browser_type="chromium", **launch_kwargs):
    async with async_playwright() as p:
        browser = await getattr(p, browser_type).launch(**launch_kwargs)
        try:
            yield browser
        finally:
            await browser.close()


@asynccontextmanager
async def simple_page(browser,base_url: str = "",viewport=None):
    context = await browser.new_context(
            base_url=base_url,
            viewport=viewport or {"width": 1280, "height": 720},
        )
    page = await context.new_page()
    try:
        yield page
    finally:
        await context.close()
        await page.close()
    
@asynccontextmanager
async def managed_page(base_url: str = "", viewport=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            base_url=base_url,
            viewport=viewport or {"width": 1280, "height": 720},
        )
        page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()
            await browser.close()