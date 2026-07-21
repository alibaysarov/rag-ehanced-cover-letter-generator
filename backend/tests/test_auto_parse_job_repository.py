import unittest

from app.models import AutoParsedJob
from app.repository.auto_parse_job_repository import AutoParseJobRepository


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    def __init__(self, value):
        self._value = value

    async def execute(self, statement):
        return FakeResult(self._value)


class AutoParseJobRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_by_id_returns_model_instance(self):
        model = AutoParsedJob(
            id=1,
            user_id=7,
            url="https://example.com",
            job_title="Python Developer",
            job_text="Need Python experience",
        )
        repository = AutoParseJobRepository(FakeSession(model))

        result = await repository.get_by_id(1)

        self.assertIs(result, model)


if __name__ == "__main__":
    unittest.main()
