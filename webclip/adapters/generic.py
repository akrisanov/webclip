from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
from urllib.parse import urljoin, urlparse

from pydantic import HttpUrl, TypeAdapter
from selectolax.parser import HTMLParser, Node
from slugify import slugify

from webclip.fetchers.base import FetchResult
from webclip.models import Asset, BlockType, ContentBlock, Document, ExtractionMetadata, Metadata

_HTTP_URL = TypeAdapter(HttpUrl)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def _node_text(node: Node) -> str:
    return node.text(separator=" ", strip=True)


def _to_http_url(value: str) -> HttpUrl:
    return _HTTP_URL.validate_python(value)


class GenericAdapter:
    name = "generic"

    def matches(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    def parse(self, result: FetchResult) -> Document:
        parser = HTMLParser(result.html)
        title = self._extract_title(parser).strip() or "Untitled"
        final_url = str(result.final_url)
        site = urlparse(final_url).netloc
        slug = (
            slugify(title)
            or sha1(final_url.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
        )

        content_root = parser.css_first("article") or parser.css_first("main") or parser.body
        content = self._extract_content_blocks(content_root, final_url)
        assets = self._extract_assets(parser, final_url)

        return Document(
            doc_id=sha1(final_url.encode("utf-8"), usedforsecurity=False).hexdigest()[:16],
            slug=slug,
            metadata=Metadata(
                site=site,
                title=title,
                source_url=_to_http_url(final_url),
            ),
            content=content,
            assets=assets,
            extraction=ExtractionMetadata(
                adapter_name=self.name,
                fetcher_name="http",
                extracted_at=datetime.now(UTC),
            ),
        )

    def _extract_title(self, parser: HTMLParser) -> str:
        og_title = parser.css_first('meta[property="og:title"]')
        if og_title is not None:
            content = (og_title.attributes.get("content") or "").strip()
            if content:
                return content
        heading = parser.css_first("h1")
        if heading is not None:
            text = _node_text(heading)
            if text:
                return text
        title_node = parser.css_first("title")
        if title_node is not None:
            return _node_text(title_node)
        return ""

    def _extract_content_blocks(self, root: Node | None, base_url: str) -> list[ContentBlock]:
        if root is None:
            return []

        blocks: list[ContentBlock] = []
        for node in root.css("h1,h2,h3,h4,h5,h6,p,blockquote,pre,code,img,li"):
            tag = node.tag.lower()
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                blocks.append(
                    ContentBlock(type=BlockType.heading, text=_node_text(node), level=int(tag[1]))
                )
                continue
            if tag in {"p", "li"}:
                text = _node_text(node)
                if text:
                    blocks.append(ContentBlock(type=BlockType.paragraph, text=text))
                continue
            if tag == "blockquote":
                text = _node_text(node)
                if text:
                    blocks.append(ContentBlock(type=BlockType.quote, text=text))
                continue
            if tag in {"pre", "code"}:
                text = _node_text(node)
                if text:
                    blocks.append(ContentBlock(type=BlockType.code, text=text))
                continue
            if tag == "img":
                src = (node.attributes.get("src") or "").strip()
                if not src:
                    continue
                absolute = urljoin(base_url, src)
                if not _is_http_url(absolute):
                    continue
                blocks.append(
                    ContentBlock(
                        type=BlockType.image,
                        url=_to_http_url(absolute),
                        caption=(node.attributes.get("alt") or "").strip() or None,
                    )
                )

        return blocks

    def _extract_assets(self, parser: HTMLParser, base_url: str) -> list[Asset]:
        assets: list[Asset] = []
        seen: set[str] = set()
        for image in parser.css("img[src]"):
            src = (image.attributes.get("src") or "").strip()
            if not src:
                continue
            absolute = urljoin(base_url, src)
            if not _is_http_url(absolute) or absolute in seen:
                continue
            seen.add(absolute)
            assets.append(Asset(source_url=_to_http_url(absolute)))
        return assets
