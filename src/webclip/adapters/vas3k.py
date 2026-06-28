from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
from urllib.parse import urljoin, urlparse

from pydantic import HttpUrl, TypeAdapter
from selectolax.parser import HTMLParser, Node
from slugify import slugify

from webclip.fetchers.base import FetchResult
from webclip.models import (
    Asset,
    BlockType,
    Comment,
    ContentBlock,
    Document,
    ExtractionMetadata,
    Metadata,
    Person,
)

_HTTP_URL = TypeAdapter(HttpUrl)


def _to_http_url(value: str) -> HttpUrl:
    return _HTTP_URL.validate_python(value)


def _node_text(node: Node) -> str:
    return node.text(separator=" ", strip=True)


class Vas3kAdapter:
    name = "vas3k"

    def matches(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host == "vas3k.club" or host.endswith(".vas3k.club")

    def parse(self, result: FetchResult) -> Document:
        parser = HTMLParser(result.html)
        final_url = str(result.final_url)
        title_node = (
            parser.css_first(".post-title")
            or parser.css_first("h1")
            or parser.css_first("title")
        )
        title = _node_text(title_node) if title_node is not None else "Untitled"

        content_root = parser.css_first(".post-text .text-body-type-post") or parser.css_first(
            ".text-body-type-post"
        )
        content = self._extract_blocks(content_root, final_url)
        comments = self._extract_comments(parser, final_url)
        assets = self._extract_assets(content, comments)

        return Document(
            doc_id=sha1(final_url.encode("utf-8"), usedforsecurity=False).hexdigest()[:16],
            slug=slugify(title) or "vas3k-post",
            metadata=Metadata(
                site="vas3k.club",
                title=title,
                source_url=_to_http_url(final_url),
            ),
            content=content,
            comments=comments,
            assets=assets,
            extraction=ExtractionMetadata(
                adapter_name=self.name,
                fetcher_name="http",
                extracted_at=datetime.now(UTC),
            ),
        )

    def _extract_comments(self, parser: HTMLParser, base_url: str) -> list[Comment]:
        comments: list[Comment] = []
        for comment_node in parser.css(".post-comments-list .comment[id^='comment-']"):
            comment_id = (comment_node.attributes.get("id") or "").replace("comment-", "")
            comments.append(
                self._parse_comment_node(
                    comment_node,
                    base_url,
                    parent_id=None,
                    comment_id=comment_id,
                )
            )

            for reply_node in comment_node.css(".comment-replies .reply[id^='comment-']"):
                reply_id = (reply_node.attributes.get("id") or "").replace("comment-", "")
                comments.append(
                    self._parse_reply_node(
                        reply_node,
                        base_url=base_url,
                        parent_id=comment_id or None,
                        comment_id=reply_id,
                    )
                )
        return comments

    def _parse_comment_node(
        self,
        comment_node: Node,
        base_url: str,
        parent_id: str | None,
        comment_id: str,
    ) -> Comment:
        author = self._parse_author(
            comment_node.css_first(".comment-header-author-name"),
            base_url,
        )
        body_node = comment_node.css_first(".comment-body .text-body-type-comment")
        body_blocks = self._extract_blocks(body_node, base_url)
        return Comment(
            comment_id=comment_id or "unknown",
            parent_id=parent_id,
            author=author,
            body=body_blocks,
        )

    def _parse_reply_node(
        self,
        reply_node: Node,
        base_url: str,
        parent_id: str | None,
        comment_id: str,
    ) -> Comment:
        author = self._parse_author(reply_node.css_first(".comment-header-author-name"), base_url)
        body_node = reply_node.css_first(".text-body-type-comment")
        body_blocks = self._extract_blocks(body_node, base_url)
        return Comment(
            comment_id=comment_id or "unknown",
            parent_id=parent_id,
            author=author,
            body=body_blocks,
        )

    def _parse_author(self, node: Node | None, base_url: str) -> Person | None:
        if node is None:
            return None
        name = _node_text(node)
        href = (node.attributes.get("href") or "").strip()
        profile_url = _to_http_url(urljoin(base_url, href)) if href else None
        return Person(name=name or "Unknown", profile_url=profile_url)

    def _extract_blocks(self, root: Node | None, base_url: str) -> list[ContentBlock]:
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
                if urlparse(absolute).scheme not in {"http", "https"}:
                    continue
                blocks.append(
                    ContentBlock(
                        type=BlockType.image,
                        url=_to_http_url(absolute),
                        caption=(node.attributes.get("alt") or "").strip() or None,
                    )
                )
        return blocks

    def _extract_assets(self, content: list[ContentBlock], comments: list[Comment]) -> list[Asset]:
        assets: list[Asset] = []
        seen: set[str] = set()

        def collect(block: ContentBlock) -> None:
            if block.type != BlockType.image or block.url is None:
                return
            url_value = str(block.url)
            if url_value in seen:
                return
            seen.add(url_value)
            assets.append(Asset(source_url=_to_http_url(url_value)))

        for block in content:
            collect(block)
        for comment in comments:
            for block in comment.body:
                collect(block)
        return assets
