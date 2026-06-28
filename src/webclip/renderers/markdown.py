from __future__ import annotations

import re

from webclip.models import BlockType, ContentBlock, Document

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def render_markdown(
    document: Document,
    include_comments: bool = True,
    asset_url_map: dict[str, str] | None = None,
) -> str:
    lines: list[str] = [
        "---",
        f'title: "{document.metadata.title}"',
        f"source_url: {document.metadata.source_url}",
        f"site: {document.metadata.site}",
        "---",
        "",
        f"# {document.metadata.title}",
        "",
    ]
    article_blocks = _prepare_article_blocks(document.content)
    toc_lines = _build_toc_lines(article_blocks)
    if toc_lines:
        lines.extend(["## Contents", ""])
        lines.extend(toc_lines)
        lines.append("")
    lines.extend(["## Article", ""])

    for block in article_blocks:
        lines.extend(
            _render_block(
                block.type,
                block.text,
                block.level,
                str(block.url) if block.url else None,
                block.caption,
                asset_url_map,
            )
        )
        lines.append("")

    if include_comments and document.comments:
        lines.extend(["## Discussion", ""])
        for comment in document.comments:
            author = comment.author.name if comment.author is not None else "Unknown"
            lines.append(f"- **{author}**")
            for body_block in comment.body:
                rendered = _render_block(
                    body_block.type,
                    body_block.text,
                    body_block.level,
                    str(body_block.url) if body_block.url else None,
                    body_block.caption,
                    asset_url_map,
                )
                for entry in rendered:
                    lines.append(f"  {entry}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _render_block(
    block_type: BlockType,
    text: str | None,
    level: int | None,
    url: str | None,
    caption: str | None,
    asset_url_map: dict[str, str] | None,
) -> list[str]:
    if block_type == BlockType.heading:
        heading_level = min(max(level or 2, 1), 6)
        return [f"{'#' * heading_level} {_normalize_internal_anchors(text or '')}".rstrip()]
    if block_type == BlockType.quote:
        return [f"> {_normalize_internal_anchors(text or '')}".rstrip()]
    if block_type == BlockType.code:
        return ["```", text or "", "```"]
    if block_type == BlockType.image and url:
        alt = caption or ""
        target_url = asset_url_map.get(url, url) if asset_url_map is not None else url
        return [f"![{alt}]({target_url})"]
    if block_type == BlockType.list:
        if not text:
            return []
        return [_normalize_internal_anchors(line).rstrip() for line in text.splitlines()]
    return [_normalize_internal_anchors(text or "")]


def _prepare_article_blocks(blocks: list[ContentBlock]) -> list[ContentBlock]:
    prepared: list[ContentBlock] = []
    has_heading = any(block.type == BlockType.heading for block in blocks)
    seen_non_image = False
    for block in blocks:
        if has_heading and not seen_non_image and block.type == BlockType.image:
            continue
        if (
            block.type == BlockType.heading
            and (block.text or "").strip().lower() in {"оглавление", "contents"}
        ):
            continue
        if block.type == BlockType.paragraph and _is_back_to_toc(block.text or ""):
            continue
        if block.type == BlockType.list and _looks_like_navigation_list(block.text or ""):
            continue
        if block.type != BlockType.image:
            seen_non_image = True
        prepared.append(block)
    return prepared


def _build_toc_lines(blocks: list[ContentBlock]) -> list[str]:
    lines: list[str] = []
    used_anchors: set[str] = set()
    for block in blocks:
        if block.type != BlockType.heading:
            continue
        level = block.level or 2
        if level not in {2, 3}:
            continue
        title = (block.text or "").strip()
        if not title:
            continue
        base = _obsidian_anchor(title)
        if not base:
            continue
        anchor = base
        suffix = 1
        while anchor in used_anchors:
            anchor = f"{base}-{suffix}"
            suffix += 1
        used_anchors.add(anchor)
        indent = "  " if level == 3 else ""
        lines.append(f"{indent}- [{title}](#{anchor})")
    return lines


def _is_back_to_toc(text: str) -> bool:
    normalized = _MARKDOWN_LINK_RE.sub(r"\1", text)
    normalized = normalized.replace("\xa0", " ").strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return (
        "назад к оглавлению" in normalized
        or "back to contents" in normalized
        or "back to toc" in normalized
    )


def _looks_like_navigation_list(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 6:
        return False
    anchor_links = 0
    for line in lines:
        match = _MARKDOWN_LINK_RE.search(line)
        if match is None:
            continue
        target = match.group(2).strip()
        if target.startswith("#"):
            anchor_links += 1
    return anchor_links / len(lines) >= 0.7


def _normalize_internal_anchors(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        label = match.group(1)
        href = match.group(2).strip()
        if not href.startswith("#"):
            return match.group(0)
        normalized = _obsidian_anchor(href[1:])
        if not normalized:
            return f"[{label}](#)"
        return f"[{label}](#{normalized})"

    return _MARKDOWN_LINK_RE.sub(replace, text)


def _obsidian_anchor(text: str) -> str:
    normalized = text.replace("\xa0", " ").strip().lower()
    normalized = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", normalized)
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    normalized = normalized.replace("_", " ")
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized.strip("-")
