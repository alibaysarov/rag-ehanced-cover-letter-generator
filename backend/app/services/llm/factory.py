"""Create the configured LangChain chat model.

The rest of the application never needs to know which LLM provider is selected.
"""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr

from app.core.config import settings


def create_chat_model(**kwargs: Any) -> BaseChatModel:
    """Return a LangChain chat model selected by the three LLM settings."""
    provider = settings.LLM_PROVIDER.strip().lower()
    model = settings.LLM_MODEL.strip()

    if not model:
        raise ValueError("LLM_MODEL must contain a provider model name.")

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model, base_url=settings.OLLAMA_HOST, **kwargs)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=SecretStr(_required_api_key(provider)),
            **kwargs,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model_name=model,
            api_key=SecretStr(_required_api_key(provider)),
            **kwargs,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER={settings.LLM_PROVIDER!r}. "
        "Choose openai, anthropic, or ollama."
    )


def _required_api_key(provider: str) -> str:
    if settings.LLM_API_KEY.strip():
        return settings.LLM_API_KEY
    raise ValueError(f"LLM_API_KEY is required when LLM_PROVIDER={provider}.")
