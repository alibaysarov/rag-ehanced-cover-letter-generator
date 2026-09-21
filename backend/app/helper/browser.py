import asyncio
import ipaddress
from urllib.parse import urlparse

from playwright.async_api import Page

from app.decorators.retry import async_retry


@async_retry()
async def get_body_from_page(page: Page, url: str) -> str:
    try:
        await page.route("**/*", secure_request_route)
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await scroll_page_bottom(page)
        await page.wait_for_timeout(500)
        body_str: str = await page.evaluate(__get_body_html())
        return body_str.strip()
    except Exception as e:
        raise


def __get_body_html() -> str:
    return """
        ()=>document.body.textContent
    """


async def scroll_page_bottom(page: Page):
    await page.evaluate("""
            () => new Promise((resolve) => {
                const distance = 300;       // пикселей за шаг
                const delay = 100;          // мс между шагами
                
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    
                    const scrolled = window.scrollY + window.innerHeight;
                    const total = document.documentElement.scrollHeight;
                    
                    if (scrolled >= total) {
                        clearInterval(timer);
                        resolve();
                    }
                }, delay);
            })
        """)


async def block_resources(route, request):
    if request.resource_type in ("image", "font", "media", "stylesheet"):
        await route.abort()
    else:
        await route.continue_()


async def secure_request_route(route, request):
    """Block browser access to local/internal networks, including subresources."""
    if request.resource_type in ("image", "font", "media", "stylesheet"):
        await route.abort()
        return
    parsed = urlparse(request.url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        await route.abort()
        return
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                await route.abort()
                return
    except (OSError, ValueError):
        await route.abort()
        return
    await route.continue_()
