from __future__ import annotations

from html import escape

from jinja2 import Environment, select_autoescape

from webclip.models import BlockType, Comment, ContentBlock, Document

SUPPORTED_THEMES = {"readable", "serif", "dark"}

_ENV = Environment(autoescape=select_autoescape(default=True))
_TEMPLATE = _ENV.from_string(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  {% if base_href %}
  <base href="{{ base_href }}">
  {% endif %}
  <style>
    :root {
      --bg: #fcfcfb;
      --surface: #ffffff;
      --text: #1f2328;
      --muted: #606770;
      --border: #e3e6ea;
      --accent: #6f56d9;
      --code-bg: #f4f5f7;
      --max-width: 760px;
    }
    body.theme-serif {
      --max-width: 780px;
      font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    }
    body.theme-dark {
      --bg: #121418;
      --surface: #171b21;
      --text: #e6e9ef;
      --muted: #a7afbb;
      --border: #2a313d;
      --accent: #9f87ff;
      --code-bg: #1f252f;
    }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, "Segoe UI", system-ui, sans-serif;
      line-height: 1.75;
      font-size: 17px;
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
    }
    main {
      max-width: var(--max-width);
      margin: 2.6rem auto;
      padding: 0 1.2rem 2rem;
    }
    h1, h2, h3, h4, h5, h6 { line-height: 1.28; letter-spacing: -0.01em; margin: 1.4em 0 0.5em; }
    p { margin: 0.9em 0; }
    img { max-width: 100%; height: auto; display: block; margin: 1rem auto; border-radius: 10px; }
    blockquote {
      border-left: 3px solid var(--accent);
      margin: 1.2rem 0;
      padding: 0.4rem 1rem;
      color: var(--muted);
    }
    pre {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.8rem;
      overflow-x: auto;
    }
    .lede {
      color: var(--muted);
      font-size: 0.97rem;
      margin-top: -0.4rem;
    }
    .discussion {
      margin-top: 2.2rem;
      padding-top: 0.8rem;
      border-top: 1px solid var(--border);
    }
    .comment-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin: 0.9rem 0;
      padding: 0.85rem 1rem;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
    .comment-level-1 { margin-left: 1.1rem; }
    .comment-level-2 { margin-left: 2.2rem; }
    .comment-level-3, .comment-level-4, .comment-level-5 { margin-left: 3rem; }
    .comment-meta {
      display: flex;
      gap: 0.6rem;
      align-items: baseline;
      margin-bottom: 0.45rem;
      color: var(--muted);
      font-size: 0.88rem;
    }
    .comment-author {
      color: var(--text);
      font-weight: 600;
      font-size: 0.92rem;
    }
    .comment-body p:first-child { margin-top: 0; }
    .comment-body p:last-child { margin-bottom: 0; }
    @media print {
      body { background: #fff; color: #111; font-size: 11.6pt; }
      main { margin: 0; max-width: 100%; padding: 0; }
      .comment-card { box-shadow: none; break-inside: avoid-page; }
      pre { white-space: pre-wrap; }
    }
  </style>
</head>
<body class="theme-{{ theme }}">
  <main>
    <h1>{{ title }}</h1>
    <p class="lede">Saved from {{ source_url }}</p>
    <section>
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
    article_html = [
        _render_block_html(block, asset_url_map=asset_url_map) for block in document.content
    ]
    comments_html = _render_comments(document.comments, asset_url_map=asset_url_map)
    return _TEMPLATE.render(
        title=document.metadata.title,
        source_url=str(document.metadata.source_url),
        article_html=article_html,
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
        timestamp = comment.created_at.isoformat() if comment.created_at is not None else None
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


def _render_block_html(block: ContentBlock, asset_url_map: dict[str, str] | None) -> str:
    if block.type == BlockType.heading:
        level = min(max(block.level or 2, 1), 6)
        text = escape(block.text or "")
        return f"<h{level}>{text}</h{level}>"
    if block.type == BlockType.quote:
        return f"<blockquote><p>{escape(block.text or '')}</p></blockquote>"
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
    return f"<p>{escape(block.text or '')}</p>"
