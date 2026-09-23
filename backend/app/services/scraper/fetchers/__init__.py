from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FetchedPage:
    url: str
    html: str


class PageFetcher(Protocol):
    async def fetch(self, url: str) -> FetchedPage: ...

    async def aclose(self) -> None: ...
