import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.llm import factory


class ChatModelFactoryTests(unittest.TestCase):
    def _settings(self, provider: str, api_key: str = ""):
        return SimpleNamespace(
            LLM_PROVIDER=provider,
            LLM_API_KEY=api_key,
            LLM_MODEL="test-model",
            OLLAMA_HOST="http://ollama.test:11434",
        )

    def test_creates_ollama_model_without_api_key(self):
        constructor = MagicMock()
        module = types.ModuleType("langchain_ollama")
        module.ChatOllama = constructor

        with (
            patch.object(factory, "settings", self._settings("ollama")),
            patch.dict(sys.modules, {"langchain_ollama": module}),
        ):
            factory.create_chat_model(temperature=0.1)

        constructor.assert_called_once_with(
            model="test-model", base_url="http://ollama.test:11434", temperature=0.1
        )

    def test_creates_openai_model_with_configured_key(self):
        constructor = MagicMock()
        module = types.ModuleType("langchain_openai")
        module.ChatOpenAI = constructor

        with (
            patch.object(factory, "settings", self._settings("openai", "test-key")),
            patch.dict(sys.modules, {"langchain_openai": module}),
        ):
            factory.create_chat_model()

        _, kwargs = constructor.call_args
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["api_key"].get_secret_value(), "test-key")

    def test_rejects_provider_that_needs_a_missing_key(self):
        with patch.object(factory, "settings", self._settings("anthropic")):
            with self.assertRaisesRegex(ValueError, "LLM_API_KEY"):
                factory.create_chat_model()

    def test_creates_anthropic_model_with_configured_key(self):
        constructor = MagicMock()
        module = types.ModuleType("langchain_anthropic")
        module.ChatAnthropic = constructor

        with (
            patch.object(factory, "settings", self._settings("anthropic", "test-key")),
            patch.dict(sys.modules, {"langchain_anthropic": module}),
        ):
            factory.create_chat_model()

        _, kwargs = constructor.call_args
        self.assertEqual(kwargs["model_name"], "test-model")
        self.assertEqual(kwargs["api_key"].get_secret_value(), "test-key")
