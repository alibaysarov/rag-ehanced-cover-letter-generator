from app.decorators.browser import simple_page
from app.pw_instances.chromium import chromium

TIMEOUT = 30_000


"""
Как зайти на сайт

1) зайти на главную
2) найти почту
3) Если есть вернуть ее
4) если нет то спарсить меню, получить ссылку на страницу "контакты" и использовать tool опять но уже со ссылкой на /contacts и спарсить оттуда
"""


async def _block_resources(route, request):
    if request.resource_type in ("image", "font", "media", "stylesheet"):
        await route.abort()
    else:
        await route.continue_()


# @tool
async def get_html(url: str):
    """
    Use this tool to extract html and markup for further use of different tools
    """

    async with simple_page(chromium, url) as page:
        try:
            await page.route("**/*", _block_resources)
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
            result = await page.evaluate("""
                () => {
                    const body = document.body.innerHTML.trim();
                    return body;
                }
            """)
            return result
        except Exception as e:
            raise e


# @tool
async def visit_website(url: str, jsFn: str):
    """
    visit_website tool for sraping page by url and executing JS code on it to get useful info
    """

    async with simple_page(chromium, url) as page:
        try:
            await page.route("**/*", _block_resources)
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
            result = await page.evaluate(jsFn)
            return result
        except Exception as e:
            raise e
