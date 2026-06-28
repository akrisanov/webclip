from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from tomllib import load

from webclip.adapters.base import SiteAdapter
from webclip.adapters.declarative import (
    DeclarativeAdapter,
    DeclarativeAdapterSpec,
    DeclarativeSelectors,
)
from webclip.adapters.generic import GenericAdapter
from webclip.adapters.vas3k import Vas3kAdapter
from webclip.config import default_declarative_adapters_dir


@dataclass(frozen=True)
class RegisteredAdapter:
    name: str
    description: str
    source: str
    factory: Callable[[], SiteAdapter] | None = None


class AdapterRegistry:
    def __init__(self, declarative_dir: Path | None = None) -> None:
        self._adapters: list[RegisteredAdapter] = [
            RegisteredAdapter(
                name="vas3k",
                description="Vas3k.club article/comments adapter",
                source="builtin",
                factory=Vas3kAdapter,
            ),
        ]
        self._adapters.extend(self._load_external_plugins())
        self._adapters.extend(
            self._load_declarative_adapters(declarative_dir or default_declarative_adapters_dir())
        )
        self._adapters.append(
            RegisteredAdapter(
                name="generic",
                description="Fallback generic HTML adapter",
                source="builtin",
                factory=GenericAdapter,
            )
        )

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

    def _load_external_plugins(self) -> list[RegisteredAdapter]:
        adapters: list[RegisteredAdapter] = []
        for ep in entry_points(group="webclip.adapters"):
            try:
                loaded = ep.load()
            except (ImportError, AttributeError):
                continue

            try:
                if isinstance(loaded, type):
                    instance = loaded()
                    adapter_name = getattr(instance, "name", ep.name)
                    adapters.append(
                        RegisteredAdapter(
                            name=adapter_name,
                            description=f"External adapter from {ep.value}",
                            source="entry-point",
                            factory=loaded,
                        )
                    )
                    continue

                if callable(loaded):
                    instance = loaded()
                    adapter_name = getattr(instance, "name", ep.name)
                    adapters.append(
                        RegisteredAdapter(
                            name=adapter_name,
                            description=f"External adapter from {ep.value}",
                            source="entry-point",
                            factory=loaded,
                        )
                    )
            except TypeError:
                continue
        return adapters

    def _load_declarative_adapters(self, adapters_dir: Path) -> list[RegisteredAdapter]:
        if not adapters_dir.exists() or not adapters_dir.is_dir():
            return []

        adapters: list[RegisteredAdapter] = []
        for path in sorted(adapters_dir.glob("*.toml")):
            with path.open("rb") as file:
                raw = load(file)
            try:
                name = str(raw["name"])
                hosts = [str(host) for host in raw["hosts"]]
            except (KeyError, TypeError):
                continue

            selectors_raw = raw.get("selectors", {})
            selectors = DeclarativeSelectors(
                title=str(selectors_raw.get("title", "h1")),
                content_root=str(selectors_raw.get("content_root", "article")),
            )
            spec = DeclarativeAdapterSpec(name=name, hosts=hosts, selectors=selectors)
            adapters.append(
                RegisteredAdapter(
                    name=spec.name,
                    description=f"Declarative adapter from {path.name}",
                    source="declarative",
                    factory=lambda spec=spec: DeclarativeAdapter(spec),
                )
            )
        return adapters
