from __future__ import annotations

from typing import Protocol

from webclip.fetchers.base import FetchResult
from webclip.models import Document


class SiteAdapter(Protocol):
    name: str

    def matches(self, url: str) -> bool: ...

    def parse(self, result: FetchResult) -> Document: ...

