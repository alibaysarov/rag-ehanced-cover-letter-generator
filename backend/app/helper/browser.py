from playwright.async_api import Page

from app.decorators.retry import async_retry


@async_retry()
async def get_body_from_page(page: Page, url: str) -> str:
    try:
        await page.route("**/*", block_resources)
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
