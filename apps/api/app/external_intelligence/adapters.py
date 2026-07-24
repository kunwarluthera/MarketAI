from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from .engine import ProviderItem


@dataclass(frozen=True)
class FetchRequest:
    query: str
    start: datetime
    end: datetime
    page: int = 1


class ProviderAdapter:
    provider = ""
    version = "1"

    def __init__(self, client=None):
        self.client = client

    def available(self) -> bool:
        return self.client is not None

    def fetch(self, request: FetchRequest) -> list[ProviderItem]:
        raise NotImplementedError


class NewsApiAdapter(ProviderAdapter):
    provider = "NEWSAPI"

    def fetch(self, request: FetchRequest) -> list[ProviderItem]:
        if self.client is None:
            return []
        return self.client.fetch(request)


class GNewsAdapter(ProviderAdapter):
    provider = "GNEWS"

    def fetch(self, request: FetchRequest) -> list[ProviderItem]:
        if self.client is None:
            return []
        return self.client.fetch(request)
