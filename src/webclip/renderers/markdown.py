from __future__ import annotations

from webclip.models import BlockType, Document


def render_markdown(document: Document, include_comments: bool = True) -> str:
    lines: list[str] = [
        "---",
        f'title: "{document.metadata.title}"',
        f"source_url: {document.metadata.source_url}",
        f"site: {document.metadata.site}",
        "---",
        "",
        f"# {document.metadata.title}",
        "",
        "## Article",
        "",
    ]

    for block in document.content:
        lines.extend(
            _render_block(
                block.type,
                block.text,
                block.level,
                str(block.url) if block.url else None,
                block.caption,
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
) -> list[str]:
    if block_type == BlockType.heading:
        heading_level = min(max(level or 2, 1), 6)
        return [f"{'#' * heading_level} {text or ''}".rstrip()]
    if block_type == BlockType.quote:
        return [f"> {text or ''}".rstrip()]
    if block_type == BlockType.code:
        return ["```", text or "", "```"]
    if block_type == BlockType.image and url:
        alt = caption or ""
        return [f"![{alt}]({url})"]
    return [text or ""]
