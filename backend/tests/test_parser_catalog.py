import json
import unittest
from unittest.mock import AsyncMock

from app.models import Parser, User
from app.services.parser_catalog import ParserCatalogService
from app.services.scraper.parser_defaults import default_parser_values


class FakeCache:
    def __init__(self):
        self.values = {}
        self.fail = False

    async def get(self, key):
        if self.fail:
            raise ConnectionError("redis unavailable")
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        if self.fail:
            raise ConnectionError("redis unavailable")
        self.values[key] = value

    async def delete(self, key):
        self.values.pop(key, None)


class ParserCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.user = User(
            id=7, email="catalog@example.test", password_hash="x", parsers_revision=4
        )
        self.session = AsyncMock()
        self.session.get.return_value = self.user
        self.cache = FakeCache()
        self.service = ParserCatalogService(self.session, self.cache)
        self.parser = Parser(id=11, **default_parser_values(7)[0])
        self.service.repository.list_all = AsyncMock(return_value=[self.parser])

    async def test_cache_miss_then_hit_returns_valid_dto(self):
        revision, first = await self.service.get_catalog(7)
        self.assertEqual(4, revision)
        self.assertEqual("hh.ru", first[0].site_key)
        self.service.repository.list_all.reset_mock()

        _, second = await self.service.get_catalog(7)
        self.assertEqual(first, second)
        self.service.repository.list_all.assert_not_awaited()

    async def test_corrupt_cache_falls_back_to_database(self):
        key = self.service.cache_key(7, 4)
        self.cache.values[key] = json.dumps({"not": "a catalog"})
        _, result = await self.service.get_catalog(7)
        self.assertEqual(1, len(result))
        self.service.repository.list_all.assert_awaited_once()

    async def test_unavailable_cache_does_not_block_database(self):
        self.cache.fail = True
        _, result = await self.service.get_catalog(7)
        self.assertEqual("hh.ru", result[0].site_key)


if __name__ == "__main__":
    unittest.main()
