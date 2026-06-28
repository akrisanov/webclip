from dataclasses import dataclass
from typing import Protocol


class Adapter(Protocol):
    name: str

    def matches(self, url: str) -> bool: ...


@dataclass(frozen=True)
class RegisteredAdapter:
    name: str
    description: str


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: list[RegisteredAdapter] = [
            RegisteredAdapter(name="generic", description="Fallback generic HTML adapter"),
            RegisteredAdapter(name="vas3k", description="Vas3k.club article/comments adapter"),
        ]

    def list_adapters(self) -> list[RegisteredAdapter]:
        return list(self._adapters)
