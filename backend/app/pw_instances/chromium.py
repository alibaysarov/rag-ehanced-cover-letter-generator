from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from app.helper import block_resources

chromium: Browser = None
_playwright: Playwright = None
context: BrowserContext = None

LAUNCH_ARGS = [
    # --- убираем то, что не нужно headless-режиму ---
    "--disable-gpu",
    "--disable-dev-shm-usage",  # критично в Docker: /dev/shm маленький, без этого Chrome может падать/тормозить
    "--disable-extensions",
    "--disable-component-extensions-with-background-pages",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-breakpad",
    "--disable-ipc-flooding-protection",
    "--disable-hang-monitor",
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-first-run",
    "--no-default-browser-check",
    "--force-color-profile=srgb",
    "--disable-features=TranslateUI,BlinkGenPropertyTrees,IsolateOrigins,site-per-process",
    # --- ключевое: не грузим то, что не нужно для парсинга текста ---
    "--blink-settings=imagesEnabled=false",  # картинки не грузятся вообще на уровне движка (быстрее, чем page.route)
]


def get_browser() -> Browser:
    if chromium is None:
        print("None chromium")
        raise RuntimeError("Browser not started. Call start_browser() first.")
    print("start chromium")
    return chromium


async def start_browser():
    global chromium, _playwright, context

    _playwright = await async_playwright().start()
    chromium = await _playwright.chromium.launch(
        headless=True,
        args=LAUNCH_ARGS,
        timeout=30000,
    )

    context = await chromium.new_context(
        viewport={
            "width": 1280,
            "height": 800,
        },  # фиксированный маленький viewport — меньше layout-работы
        java_script_enabled=True,  # обязательно, вам нужен JS для evaluate
        bypass_csp=True,  # иногда ускоряет/не мешает route-перехвату
    )
    # роут можно повесить один раз на весь context, а не на каждую page
    await context.route("**/*", block_resources)
    print("Browser started")


async def close_browser():
    global chromium, _playwright
    if chromium:
        await chromium.close()
    if _playwright:
        await _playwright.stop()
    print("Browser closed")
