from playwright.async_api import Browser, Playwright, async_playwright

chromium: Browser = None
_playwright: Playwright = None



def get_browser() -> Browser:
    if chromium is None:
        print("None chromium")
        raise RuntimeError("Browser not started. Call start_browser() first.")
    print("start chromium")
    return chromium


async def start_browser():
    global chromium, _playwright
    _playwright = await async_playwright().start()
    chromium = await _playwright.chromium.launch(
        headless=True,
        executable_path="./browsers/chromium-1187/chrome-linux/chrome"
    )
    print("Browser started")

async def close_browser():
    global chromium, _playwright
    if chromium:
        await chromium.close()
    if _playwright:
        await _playwright.stop()
    print("Browser closed")