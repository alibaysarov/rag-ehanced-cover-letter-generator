from openai import OpenAI
from app.services.embeddings.base import BaseEmbedder

_MODEL = "text-embedding-3-large"
_DIMENSIONS = 3072


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, model: str = _MODEL, dimensions: int = _DIMENSIONS):
        self._model = model
        self._dimensions = dimensions
        self._client = OpenAI()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self._model,
            dimensions=self._dimensions,
            input=texts,
        )
        return [item.embedding for item in response.data]
