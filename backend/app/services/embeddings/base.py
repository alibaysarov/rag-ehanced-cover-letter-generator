from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Размерность векторов, которые возвращает данная модель."""
        ...

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Преобразует список строк в список эмбеддинг-векторов."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Удобный метод для одной строки — используется при поиске по запросу."""
        return self.embed_texts([text])[0]
