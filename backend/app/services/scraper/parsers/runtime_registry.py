from app.schemas.parser import ParserSnapshot
from app.services.scraper.fetchers.http import HttpxPageFetcher
from app.services.scraper.fetchers.playwright import PlaywrightPageFetcher
from app.services.scraper.parsers.configured import ConfiguredVacancyParser
from app.services.scraper.parsers.selector_runtime import SelectorParserRuntime


class LegacyPlaywrightParserRuntime:
    def __init__(self, snapshot, browser):
        self.parser = ConfiguredVacancyParser(snapshot)
        self.browser = browser
        self.context = None

    async def get_list(self, text, job_id):
        return await self.parser.get_list(self.browser, text, job_id)

    async def parse_single_vacancy(self, vacancy_id):
        if self.context is None:
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
        page = await self.context.new_page()
        try:
            return await self.parser.parse_single_vacancy(page, vacancy_id)
        finally:
            await page.close()

    async def aclose(self):
        if self.context is not None:
            await self.context.close()


def create_runtime(snapshot: ParserSnapshot | dict, browser=None):
    config = ParserSnapshot.model_validate(snapshot)
    if config.extraction_engine == "selectors_v1" and config.fetch_mode == "http":
        return SelectorParserRuntime(config, HttpxPageFetcher(config.request_config))
    if config.extraction_engine == "legacy_js" and browser is not None:
        return LegacyPlaywrightParserRuntime(config, browser)
    if (
        config.extraction_engine == "selectors_v1"
        and config.fetch_mode == "playwright"
        and browser is not None
    ):
        return SelectorParserRuntime(
            config, PlaywrightPageFetcher(browser, config.request_config)
        )
    raise NotImplementedError(
        "only selectors_v1 + http runtime is currently implemented"
    )
