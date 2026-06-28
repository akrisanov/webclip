from __future__ import annotations

import re
from datetime import datetime
from html import escape
from urllib.parse import unquote, urlparse

from jinja2 import Environment, select_autoescape
from slugify import slugify

from webclip.models import BlockType, Comment, ContentBlock, Document

SUPPORTED_THEMES = {"readable", "serif", "dark"}

_ENV = Environment(autoescape=select_autoescape(default=True))
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_INLINE_TOKEN_RE = re.compile(
    r"\[([^\]]+)\]\(([^)]+)\)|https?://[^\s<>()]+|\*\*([^*]+)\*\*|__([^_]+)__|`([^`]+)`|\*([^*]+)\*|_([^_]+)_"
)
_TEMPLATE = _ENV.from_string(
    """<!doctype html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  {% if base_href %}
  <base href="{{ base_href }}">
  {% endif %}
  <style>
    :root {
      --bg: #f3f4f7;
      --surface: #ffffff;
      --text: #202733;
      --muted: #657286;
      --border: #e2e7ef;
      --accent: #5b6df7;
      --code-bg: #f3f5f9;
      --link: #3b5bdb;
      --max-width: 760px;
      --body-size: 18px;
      --article-leading: 1.76;
    }
    body.theme-readable {
      font-family: Inter, "Segoe UI", system-ui, sans-serif;
    }
    body.theme-serif {
      --max-width: 78ch;
      --body-size: 18.5px;
      --article-leading: 1.82;
      font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    }
    body.theme-dark {
      --bg: #0f131a;
      --surface: #151b24;
      --text: #e3e9f4;
      --muted: #a2aec2;
      --border: #2c3644;
      --accent: #9f87ff;
      --code-bg: #1d2531;
    }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      line-height: var(--article-leading);
      font-size: var(--body-size);
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
    }
    a {
      color: var(--link);
      text-decoration: none;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    a:hover { text-decoration: underline; }
    main {
      max-width: var(--max-width);
      margin: 2.2rem auto 3rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 2rem 2rem 2.6rem;
      box-shadow: 0 4px 18px rgba(20, 35, 72, 0.05);
    }
    h1, h2, h3, h4, h5, h6 {
      line-height: 1.27;
      letter-spacing: -0.01em;
      margin: 1.36em 0 0.5em;
      color: var(--text);
      scroll-margin-top: 1rem;
    }
    h1 { font-size: 2rem; margin-top: 0.05rem; margin-bottom: 0.55rem; }
    .article h1 {
      font-size: 1.92rem;
      margin-top: 2.35rem;
      margin-bottom: 0.9rem;
      letter-spacing: -0.012em;
      font-weight: 650;
      line-height: 1.28;
    }
    .article h2 {
      font-size: 1.52rem;
      margin-top: 2.1rem;
      margin-bottom: 0.72rem;
      font-weight: 640;
      line-height: 1.3;
      border-top: none;
      padding-top: 0;
    }
    .article h3 {
      font-size: 1.26rem;
      margin-top: 1.55rem;
      margin-bottom: 0.5rem;
      font-weight: 620;
      color: color-mix(in srgb, var(--text) 88%, var(--muted));
      letter-spacing: -0.004em;
    }
    .toc > h2,
    .article > h2,
    .discussion > h2 {
      color: var(--muted);
      font-size: 0.95rem;
      font-weight: 520;
      letter-spacing: 0.01em;
      border-bottom: none;
      padding-bottom: 0.1rem;
      margin-top: 0.7rem;
    }
    .toc {
      margin: 1.1rem 0 2rem;
      padding: 0.95rem 1.05rem;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #fafbff;
      scroll-margin-top: 1rem;
    }
    .toc ol {
      margin: 0.6rem 0 0;
      padding-left: 1.1rem;
      line-height: 1.55;
    }
    .toc li { margin: 0.25rem 0; }
    .toc li.toc-level-3 {
      margin-left: 1rem;
      font-size: 0.96em;
    }
    .toc a { color: var(--text); }
    p, li, blockquote {
      margin: 1em 0;
      overflow-wrap: break-word;
    }
    ul, ol {
      margin: 0.95rem 0 1.25rem;
      padding-left: 1.45rem;
    }
    li {
      margin: 0.42rem 0;
      line-height: 1.66;
      padding-left: 0.12rem;
    }
    li::marker {
      color: color-mix(in srgb, var(--muted) 78%, var(--text));
      font-weight: 560;
    }
    .article ul {
      list-style-type: disc;
    }
    .article ul ul {
      list-style-type: circle;
      margin-top: 0.42rem;
      margin-bottom: 0.7rem;
    }
    .article ol {
      list-style-type: decimal;
    }
    .article ul.list-steps,
    .article ol.list-steps {
      margin-top: 1.1rem;
      margin-bottom: 1.45rem;
    }
    .article ul.list-steps > li,
    .article ol.list-steps > li {
      margin: 0.58rem 0;
    }
    .article li > p {
      margin: 0.35rem 0;
    }
    img {
      max-width: 100%;
      height: auto;
      display: block;
      margin: 1.45rem auto;
      border-radius: 12px;
      border: 1px solid var(--border);
      break-inside: avoid-page;
      page-break-inside: avoid;
    }
    blockquote {
      border-left: 3px solid var(--accent);
      margin: 1.2rem 0;
      padding: 0.35rem 1rem;
      color: var(--muted);
    }
    pre {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.9rem 1rem;
      overflow-x: auto;
    }
    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.92em;
    }
    .lede {
      color: var(--muted);
      font-size: 0.92rem;
      margin-top: -0.2rem;
      margin-bottom: 1.25rem;
      word-break: break-word;
    }
    .discussion {
      margin-top: 2.7rem;
      padding-top: 1.2rem;
      border-top: 1px solid var(--border);
    }
    .quick-nav {
      position: fixed;
      right: 1rem;
      bottom: 1rem;
      display: flex;
      gap: 0.45rem;
      z-index: 30;
    }
    .quick-nav a {
      background: color-mix(in srgb, var(--surface) 90%, #fff);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 0.82rem;
      line-height: 1;
      border-radius: 999px;
      padding: 0.45rem 0.62rem;
      box-shadow: 0 3px 10px rgba(20, 35, 72, 0.08);
      text-decoration: none;
    }
    .quick-nav a:hover {
      background: color-mix(in srgb, var(--surface) 76%, #fff);
      text-decoration: none;
    }
    .comment-card {
      background: #fafbfe;
      border: 1px solid var(--border);
      border-left: 3px solid #d8def0;
      border-radius: 8px;
      margin: 0.85rem 0;
      padding: 0.8rem 0.9rem;
    }
    .comment-level-1 { margin-left: 1.05rem; }
    .comment-level-2 { margin-left: 2.1rem; }
    .comment-level-3, .comment-level-4, .comment-level-5 { margin-left: 3rem; }
    .comment-meta {
      display: flex;
      gap: 0.55rem;
      align-items: baseline;
      margin-bottom: 0.32rem;
      color: var(--muted);
      font-size: 0.8rem;
    }
    .comment-author {
      color: var(--text);
      font-weight: 600;
      font-size: 0.86rem;
    }
    .comment-body p:first-child { margin-top: 0; }
    .comment-body p:last-child { margin-bottom: 0; }
    .comment-body { font-size: 0.95em; line-height: 1.64; }
    @media (max-width: 900px) {
      main {
        margin: 1rem 0.6rem 1.5rem;
        border-radius: 12px;
        padding: 1.3rem 1rem 1.5rem;
        box-shadow: none;
      }
      body { font-size: 17px; }
      .article h1 { font-size: 1.7rem; }
      .article h2 { font-size: 1.4rem; }
      .article h3 { font-size: 1.18rem; }
      .comment-level-1 { margin-left: 0.65rem; }
      .comment-level-2 { margin-left: 1.15rem; }
      .comment-level-3, .comment-level-4, .comment-level-5 { margin-left: 1.5rem; }
      .quick-nav { right: 0.65rem; bottom: 0.65rem; }
    }
    @media print {
      @page {
        size: 148mm 210mm;
        margin: 18mm 16mm 20mm;
      }
      body { background: #fff; color: #111; font-size: 12.5pt; line-height: 1.62; }
      main {
        margin: 0 auto;
        max-width: 100%;
        padding: 0;
        border: none;
        border-radius: 0;
        background: #fff;
        box-shadow: none;
      }
      .article { margin-top: 0.8rem; }
      h1, h2, h3, h4, h5, h6 { color: #111; page-break-after: avoid; }
      .toc { page-break-after: always; background: #fff; }
      .comment-card {
        break-inside: avoid-page;
        page-break-inside: avoid;
        background: #fafafa;
      }
      .quick-nav { display: none; }
      pre { white-space: pre-wrap; }
    }
  </style>
</head>
<body class="theme-{{ theme }}">
  <main id="top">
    <h1>{{ title }}</h1>
    <p class="lede">Saved from {{ source_url }}</p>
    {% if toc_items %}
    <section class="toc" id="contents">
      <h2>Contents</h2>
      <ol>
        {% for item in toc_items %}
        <li class="toc-level-{{ item.level }}">
          <a href="#{{ item.anchor }}">{{ item.title }}</a>
        </li>
        {% endfor %}
      </ol>
    </section>
    {% endif %}
    <section class="article">
      <h2>Article</h2>
      {% for html in article_html %}
      {{ html | safe }}
      {% endfor %}
    </section>
    {% if include_comments and comments_html %}
    <section class="discussion">
      <h2>Discussion</h2>
      {% for comment in comments_html %}
      <article class="comment-card comment-level-{{ comment.level }}">
        <div class="comment-meta">
          <span class="comment-author">{{ comment.author }}</span>
          {% if comment.timestamp %}
          <span>{{ comment.timestamp }}</span>
          {% endif %}
          {% if comment.score %}
          <span>▲ {{ comment.score }}</span>
          {% endif %}
        </div>
        <div class="comment-body">
          {% for html in comment.body %}
          {{ html | safe }}
          {% endfor %}
        </div>
      </article>
      {% endfor %}
    </section>
    {% endif %}
  </main>
  <nav class="quick-nav" aria-label="Quick navigation">
    <a href="#contents">Contents</a>
    <a href="#top">Top</a>
  </nav>
</body>
</html>
"""
)


def render_html(
    document: Document,
    include_comments: bool = True,
    theme: str = "readable",
    asset_url_map: dict[str, str] | None = None,
    base_href: str | None = None,
) -> str:
    if theme not in SUPPORTED_THEMES:
        msg = f"Unsupported HTML theme: {theme}"
        raise ValueError(msg)
    reading_blocks = _prepare_article_blocks(document.content)
    article_html, toc_items = _render_article_blocks(
        blocks=reading_blocks,
        asset_url_map=asset_url_map,
    )
    comments_html = _render_comments(document.comments, asset_url_map=asset_url_map)
    return _TEMPLATE.render(
        lang=_infer_language(document),
        title=document.metadata.title,
        source_url=str(document.metadata.source_url),
        article_html=article_html,
        toc_items=toc_items,
        comments_html=comments_html,
        include_comments=include_comments,
        theme=theme,
        base_href=base_href,
    )


def _render_comments(
    comments: list[Comment],
    asset_url_map: dict[str, str] | None,
) -> list[dict[str, str | int | list[str] | None]]:
    depth_map = _build_depth_map(comments)
    rendered: list[dict[str, str | int | list[str] | None]] = []
    for comment in comments:
        author = comment.author.name if comment.author is not None else "Unknown"
        timestamp = _format_timestamp(comment.created_at)
        depth = min(max(depth_map.get(comment.comment_id, 0), 0), 5)
        rendered.append(
            {
                "author": author,
                "timestamp": timestamp,
                "score": comment.score,
                "level": depth,
                "body": [
                    _render_block_html(block, asset_url_map=asset_url_map)
                    for block in comment.body
                ],
            }
        )
    return rendered


def _format_timestamp(timestamp: datetime | None) -> str | None:
    if timestamp is None:
        return None
    return timestamp.astimezone().strftime("%Y-%m-%d %H:%M")


def _build_depth_map(comments: list[Comment]) -> dict[str, int]:
    by_id = {comment.comment_id: comment for comment in comments}
    depth_map: dict[str, int] = {}
    for comment in comments:
        depth = 0
        parent_id = comment.parent_id
        visited: set[str] = set()
        while parent_id is not None and parent_id not in visited:
            visited.add(parent_id)
            parent = by_id.get(parent_id)
            if parent is None:
                break
            depth += 1
            parent_id = parent.parent_id
        depth_map[comment.comment_id] = depth
    return depth_map


def _render_block_html(
    block: ContentBlock,
    asset_url_map: dict[str, str] | None,
    heading_anchor: str | None = None,
) -> str:
    if block.type == BlockType.heading:
        level = min(max(block.level or 2, 1), 6)
        text = escape(block.text or "")
        anchor = heading_anchor or slugify(block.text or "", separator="-", lowercase=True)
        attr = f' id="{escape(anchor)}"' if anchor else ""
        return f"<h{level}{attr}>{text}</h{level}>"
    if block.type == BlockType.quote:
        return f"<blockquote><p>{_render_inline_text(block.text or '')}</p></blockquote>"
    if block.type == BlockType.list:
        lines = [line.strip() for line in (block.text or "").splitlines() if line.strip()]
        if not lines:
            return ""
        cleaned_items: list[str] = []
        seen_keys: set[str] = set()
        for line in lines:
            item = re.sub(r"^([-*]|\d+\.)\s+", "", line, count=1)
            dedupe_key = _dedupe_key(item)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            cleaned_items.append(item)
        if not cleaned_items:
            return ""
        list_class = " class=\"list-steps\"" if _looks_like_step_list(cleaned_items) else ""
        items = [f"<li>{_render_inline_text(item)}</li>" for item in cleaned_items]
        return f"<ul{list_class}>" + "".join(items) + "</ul>"
    if block.type == BlockType.code:
        return f"<pre><code>{escape(block.text or '')}</code></pre>"
    if block.type == BlockType.image and block.url is not None:
        caption = f' alt="{escape(block.caption)}"' if block.caption else ""
        source_url = str(block.url)
        localized = (
            asset_url_map.get(source_url, source_url)
            if asset_url_map is not None
            else source_url
        )
        return f'<img src="{escape(localized)}"{caption}>'
    paragraphs = _split_long_paragraph(block.text or "")
    rendered_paragraphs = [f"<p>{_render_inline_text(entry)}</p>" for entry in paragraphs]
    return "".join(rendered_paragraphs)


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


def _render_article_blocks(
    blocks: list[ContentBlock],
    asset_url_map: dict[str, str] | None,
) -> tuple[list[str], list[dict[str, str | int]]]:
    rendered: list[str] = []
    toc_items: list[dict[str, str | int]] = []
    used_anchors: set[str] = set()
    for block in blocks:
        heading_anchor: str | None = None
        if block.type == BlockType.heading:
            title = (block.text or "").strip()
            base = slugify(title, separator="-", lowercase=True)
            if base:
                level = block.level or 2
                heading_anchor = base
                suffix = 2
                while heading_anchor in used_anchors:
                    heading_anchor = f"{base}-{suffix}"
                    suffix += 1
                used_anchors.add(heading_anchor)
                if level in {2, 3}:
                    toc_items.append(
                        {"title": title, "anchor": heading_anchor, "level": level}
                    )
        rendered.append(
            _render_block_html(
                block,
                asset_url_map=asset_url_map,
                heading_anchor=heading_anchor,
            )
        )
    return rendered, toc_items


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


def _render_inline_text(text: str) -> str:
    output: list[str] = []
    position = 0
    for match in _INLINE_TOKEN_RE.finditer(text):
        output.append(escape(text[position : match.start()]))
        token = match.group(0)
        link_label, link_href = match.group(1), match.group(2)
        if link_label is not None and link_href is not None:
            normalized_href = _normalize_link_href(link_href.strip())
            label_value = link_label.strip()
            if label_value == link_href.strip():
                label_value = _shorten_url_label(link_href.strip())
            label = escape(label_value)
            href = escape(normalized_href, quote=True)
            output.append(f'<a href="{href}">{label}</a>')
        elif token.startswith(("http://", "https://")):
            href = escape(token, quote=True)
            label = escape(_shorten_url_label(token))
            output.append(f'<a href="{href}">{label}</a>')
        elif match.group(3) is not None or match.group(4) is not None:
            strong_text = match.group(3) or match.group(4) or ""
            output.append(f"<strong>{escape(strong_text)}</strong>")
        elif match.group(5) is not None:
            output.append(f"<code>{escape(match.group(5))}</code>")
        else:
            emphasis_text = match.group(6) or match.group(7) or ""
            output.append(f"<em>{escape(emphasis_text)}</em>")
        position = match.end()
    output.append(escape(text[position:]))
    return "".join(output).replace("\n", "<br>")


def _normalize_link_href(href_raw: str) -> str:
    if href_raw.startswith("#"):
        fragment = unquote(href_raw[1:])
        normalized = slugify(fragment, separator="-", lowercase=True)
        return f"#{normalized}" if normalized else "#"
    return href_raw


def _shorten_url_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path.rstrip("/")
    if len(path) > 28:
        path = f"{path[:28]}..."
    if path:
        return f"{host}{path}"
    return host


def _dedupe_key(text: str) -> str:
    normalized = text.replace("\xa0", " ").strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = _MARKDOWN_LINK_RE.sub(r"\1", normalized)
    return normalized


def _looks_like_step_list(items: list[str]) -> bool:
    if len(items) < 4:
        return False
    long_items = sum(1 for item in items if len(item) >= 75)
    return long_items >= max(2, len(items) // 3)


def _split_long_paragraph(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    chunks = [chunk.strip() for chunk in normalized.split("\n\n") if chunk.strip()]
    if len(chunks) > 1:
        return chunks
    if len(normalized) < 360:
        return [normalized]
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    if len(sentences) < 2:
        return [normalized]
    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        sentence_len = len(stripped) + (1 if current else 0)
        if current and current_len + sentence_len > 280:
            parts.append(" ".join(current))
            current = [stripped]
            current_len = len(stripped)
        else:
            current.append(stripped)
            current_len += sentence_len
    if current:
        parts.append(" ".join(current))
    return parts or [normalized]


def _infer_language(document: Document) -> str:
    if re.search(r"[\u0400-\u04FF]", document.metadata.title):
        return "ru"
    probe = [document.metadata.title]
    for block in document.content[:20]:
        if block.text:
            probe.append(block.text)
    sample = " ".join(probe)
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", sample))
    latin = len(re.findall(r"[a-zA-Z]", sample))
    return "ru" if cyrillic >= latin else "en"
