import unittest
from unittest.mock import patch

import httpx

from app.schemas.parser import RequestConfig
from app.services.scraper.fetchers.http import HttpxPageFetcher


class HttpxPageFetcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_redirect_returns_final_url_and_html(self):
        def handler(request):
            if request.url.path == "/start":
                return httpx.Response(302, headers={"location": "/final"})
            return httpx.Response(
                200, headers={"content-type": "text/html"}, text="<html>ok</html>"
            )

        fetcher = HttpxPageFetcher(RequestConfig(max_retries=0))
        await fetcher.client.aclose()
        fetcher.client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        )
        try:
            with patch(
                "app.services.scraper.fetchers.http.validate_public_url_async",
                return_value="https://jobs.test/start",
            ):
                result = await fetcher.fetch("https://jobs.test/start")
            self.assertEqual(result.url, "https://jobs.test/final")
            self.assertIn("ok", result.html)
        finally:
            await fetcher.aclose()

    async def test_retries_transient_status(self):
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(503)
            return httpx.Response(200, headers={"content-type": "text/html"}, text="ok")

        config = RequestConfig(max_retries=1, retry_base_delay_seconds=0.1)
        fetcher = HttpxPageFetcher(config)
        await fetcher.client.aclose()
        fetcher.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            with patch(
                "app.services.scraper.fetchers.http.validate_public_url_async",
                return_value="https://jobs.test",
            ):
                result = await fetcher.fetch("https://jobs.test")
            self.assertEqual(result.html, "ok")
            self.assertEqual(calls, 2)
        finally:
            await fetcher.aclose()

    async def test_does_not_retry_client_error(self):
        calls = 0

        def handler(request):
            nonlocal calls
            calls += 1
            return httpx.Response(404)

        fetcher = HttpxPageFetcher(RequestConfig(max_retries=2))
        await fetcher.client.aclose()
        fetcher.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            with self.assertRaises(httpx.HTTPStatusError):
                with patch(
                    "app.services.scraper.fetchers.http.validate_public_url_async",
                    return_value="https://jobs.test",
                ):
                    await fetcher.fetch("https://jobs.test")
            self.assertEqual(calls, 1)
        finally:
            await fetcher.aclose()


if __name__ == "__main__":
    unittest.main()
