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


def _normalize_inline_text(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.splitlines()]
    return "\n".join(lines).strip()


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
        for node in root.iter():
            self._collect_blocks_from_node(node=node, base_url=base_url, blocks=blocks)
        return blocks

    def _collect_blocks_from_node(
        self,
        node: Node,
        base_url: str,
        blocks: list[ContentBlock],
    ) -> None:
        tag = node.tag.lower()
        if tag in {"script", "style"}:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            blocks.append(
                ContentBlock(
                    type=BlockType.heading,
                    text=_node_text(node),
                    level=int(tag[1]),
                )
            )
            return
        if tag == "p":
            text = self._render_inline_markdown(node, base_url)
            if text:
                blocks.append(ContentBlock(type=BlockType.paragraph, text=text))
            for image_node in node.css("img"):
                self._collect_blocks_from_node(node=image_node, base_url=base_url, blocks=blocks)
            return
        if tag in {"ul", "ol"}:
            lines: list[str] = []
            for index, item in enumerate(node.css("li"), start=1):
                item_text = self._render_inline_markdown(item, base_url)
                if not item_text:
                    continue
                prefix = f"{index}. " if tag == "ol" else "- "
                lines.append(f"{prefix}{item_text}")
            if lines:
                blocks.append(ContentBlock(type=BlockType.list, text="\n".join(lines)))
            return
        if tag == "blockquote":
            text = self._render_inline_markdown(node, base_url)
            if text:
                blocks.append(ContentBlock(type=BlockType.quote, text=text))
            return
        if tag == "pre":
            text = node.text(separator="\n", strip=True)
            if text:
                blocks.append(ContentBlock(type=BlockType.code, text=text))
            return
        if tag == "code":
            parent_tag = node.parent.tag.lower() if node.parent is not None else ""
            if parent_tag != "pre":
                return
            text = node.text(separator="\n", strip=True)
            if text:
                blocks.append(ContentBlock(type=BlockType.code, text=text))
            return
        if tag == "img":
            src = (node.attributes.get("src") or "").strip()
            if not src:
                return
            absolute = urljoin(base_url, src)
            if urlparse(absolute).scheme not in {"http", "https"}:
                return
            blocks.append(
                ContentBlock(
                    type=BlockType.image,
                    url=_to_http_url(absolute),
                    caption=(node.attributes.get("alt") or "").strip() or None,
                )
            )
            return
        for child in node.iter():
            self._collect_blocks_from_node(node=child, base_url=base_url, blocks=blocks)

    def _render_inline_markdown(self, node: Node, base_url: str) -> str:
        chunks: list[str] = []
        child = node.child
        while child is not None:
            tag = child.tag.lower()
            if tag == "-text":
                chunks.append(child.text())
            elif tag == "br":
                chunks.append("\n")
            elif tag == "a":
                rendered = self._render_inline_markdown(child, base_url)
                label = _normalize_inline_text(rendered or child.text())
                href = (child.attributes.get("href") or "").strip()
                if href.startswith("#"):
                    fragment = href[1:].strip().lower()
                    target = f"#{fragment}" if fragment else ""
                else:
                    target = urljoin(base_url, href) if href else ""
                if label and target:
                    chunks.append(f"[{label}]({target})")
                elif label:
                    chunks.append(label)
            elif tag in {"strong", "b"}:
                value = _normalize_inline_text(self._render_inline_markdown(child, base_url))
                chunks.append(f"**{value}**" if value else "")
            elif tag in {"em", "i"}:
                value = _normalize_inline_text(self._render_inline_markdown(child, base_url))
                chunks.append(f"*{value}*" if value else "")
            elif tag == "code":
                value = _normalize_inline_text(child.text(separator=" ", strip=True))
                chunks.append(f"`{value}`" if value else "")
            elif tag == "img":
                pass
            else:
                nested = self._render_inline_markdown(child, base_url)
                chunks.append(nested or child.text(separator=" ", strip=True))
            child = child.next
        return _normalize_inline_text("".join(chunks))

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
