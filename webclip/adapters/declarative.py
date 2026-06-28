from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
from urllib.parse import urljoin, urlparse

from pydantic import HttpUrl, TypeAdapter
from selectolax.parser import HTMLParser, Node
from slugify import slugify

from webclip.fetchers.base import FetchResult
from webclip.models import Asset, BlockType, ContentBlock, Document, ExtractionMetadata, Metadata

_HTTP_URL = TypeAdapter(HttpUrl)


def _to_http_url(value: str) -> HttpUrl:
    return _HTTP_URL.validate_python(value)


@dataclass(frozen=True)
class DeclarativeSelectors:
    title: str = "h1"
    content_root: str = "article"


@dataclass(frozen=True)
class DeclarativeAdapterSpec:
    name: str
    hosts: list[str]
    selectors: DeclarativeSelectors


class DeclarativeAdapter:
    def __init__(self, spec: DeclarativeAdapterSpec) -> None:
        self._spec = spec
        self.name = spec.name

    def matches(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host == rule or host.endswith(f".{rule}") for rule in self._spec.hosts)

    def parse(self, result: FetchResult) -> Document:
        parser = HTMLParser(result.html)
        final_url = str(result.final_url)
        title_node = parser.css_first(self._spec.selectors.title) or parser.css_first("title")
        title = title_node.text(strip=True) if title_node is not None else "Untitled"
        content_root = parser.css_first(self._spec.selectors.content_root) or parser.body
        content = self._extract_content(content_root, final_url)

        return Document(
            doc_id=sha1(final_url.encode("utf-8"), usedforsecurity=False).hexdigest()[:16],
            slug=slugify(title) or "declarative-page",
            metadata=Metadata(
                site=urlparse(final_url).netloc,
                title=title,
                source_url=_to_http_url(final_url),
            ),
            content=content,
            assets=self._extract_assets(content),
            extraction=ExtractionMetadata(
                adapter_name=self.name,
                fetcher_name="http",
                extracted_at=datetime.now(UTC),
            ),
        )

    def _extract_content(self, root: Node | None, base_url: str) -> list[ContentBlock]:
        if root is None:
            return []
        blocks: list[ContentBlock] = []
        for node in root.css("h1,h2,h3,h4,h5,h6,p,blockquote,pre,code,img,li"):
            tag = node.tag.lower()
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                blocks.append(
                    ContentBlock(
                        type=BlockType.heading,
                        text=node.text(strip=True),
                        level=int(tag[1]),
                    )
                )
            elif tag in {"p", "li"}:
                text = node.text(strip=True)
                if text:
                    blocks.append(ContentBlock(type=BlockType.paragraph, text=text))
            elif tag == "blockquote":
                text = node.text(strip=True)
                if text:
                    blocks.append(ContentBlock(type=BlockType.quote, text=text))
            elif tag in {"pre", "code"}:
                text = node.text(strip=True)
                if text:
                    blocks.append(ContentBlock(type=BlockType.code, text=text))
            elif tag == "img":
                src = (node.attributes.get("src") or "").strip()
                if src:
                    blocks.append(
                        ContentBlock(
                            type=BlockType.image,
                            url=_to_http_url(urljoin(base_url, src)),
                            caption=(node.attributes.get("alt") or "").strip() or None,
                        )
                    )
        return blocks

    def _extract_assets(self, blocks: list[ContentBlock]) -> list[Asset]:
        assets: list[Asset] = []
        seen: set[str] = set()
        for block in blocks:
            if block.type != BlockType.image or block.url is None:
                continue
            url_value = str(block.url)
            if url_value in seen:
                continue
            seen.add(url_value)
            assets.append(Asset(source_url=_to_http_url(url_value)))
        return assets
