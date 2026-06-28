from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from webclip.adapters.base import SiteAdapter
from webclip.adapters.generic import GenericAdapter


@dataclass(frozen=True)
class RegisteredAdapter:
    name: str
    description: str
    factory: Callable[[], SiteAdapter] | None = None


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: list[RegisteredAdapter] = [
            RegisteredAdapter(
                name="generic",
                description="Fallback generic HTML adapter",
                factory=GenericAdapter,
            ),
            RegisteredAdapter(name="vas3k", description="Vas3k.club article/comments adapter"),
        ]

    def list_adapters(self) -> list[RegisteredAdapter]:
        return list(self._adapters)

    def resolve(self, url: str) -> SiteAdapter:
        for registered in self._adapters:
            if registered.factory is None:
                continue
            adapter = registered.factory()
            if adapter.matches(url):
                return adapter
        msg = f"No adapter available for URL: {url}"
        raise ValueError(msg)
