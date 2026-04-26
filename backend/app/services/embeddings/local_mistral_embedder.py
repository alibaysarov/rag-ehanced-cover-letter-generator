import os
from langchain_ollama import OllamaEmbeddings
from app.services.embeddings.base import BaseEmbedder

# Модель должна быть предварительно загружена через `ollama pull nomic-embed-text`.
# ВАЖНО: при использовании этого эмбеддера нужно пересоздать Qdrant-коллекции
# с vector_size=768 (nomic-embed-text) вместо 3072 у OpenAI text-embedding-3-large.
_MODEL = "nomic-embed-text:latest"
_DIMENSIONS = 768


class LocalMistralEmbedder(BaseEmbedder):
    def __init__(self, model: str = _MODEL):
        self._model = model
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._embedder = OllamaEmbeddings(model=model, base_url=base_url)

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._embedder.embed_documents(texts)
