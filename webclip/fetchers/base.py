from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FetchRequest:
    url: str
    requires_auth: bool = False


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    status_code: int
    html: str


class Fetcher(Protocol):
    name: str

    async def fetch(self, request: FetchRequest) -> FetchResult: ...

