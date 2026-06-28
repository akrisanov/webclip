from __future__ import annotations

from html import escape

from jinja2 import Environment, select_autoescape

from webclip.models import BlockType, Comment, ContentBlock, Document

_ENV = Environment(autoescape=select_autoescape(default=True))
_TEMPLATE = _ENV.from_string(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <style>
    body {
      max-width: 760px;
      margin: 2rem auto;
      line-height: 1.7;
      font-family: Inter, system-ui, sans-serif;
    }
    h1,h2,h3 { line-height: 1.25; }
    img { max-width: 100%; height: auto; display: block; margin: 1rem 0; }
    blockquote { border-left: 3px solid #ddd; margin: 1rem 0; padding: 0.3rem 1rem; color: #444; }
    pre { background: #f7f7f7; padding: 0.75rem; overflow-x: auto; }
    .comment { margin: 1rem 0 1.25rem; padding-left: 0.75rem; border-left: 2px solid #ececec; }
    .comment-meta { color: #666; font-size: 0.9rem; margin-bottom: 0.4rem; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  <section>
    <h2>Article</h2>
    {% for html in article_html %}
    {{ html | safe }}
    {% endfor %}
  </section>
  {% if include_comments and comments_html %}
  <section>
    <h2>Discussion</h2>
    {% for comment in comments_html %}
    <div class="comment">
      <div class="comment-meta">{{ comment.author }}</div>
      {% for html in comment.body %}
      {{ html | safe }}
      {% endfor %}
    </div>
    {% endfor %}
  </section>
  {% endif %}
</body>
</html>
"""
)


def render_html(document: Document, include_comments: bool = True) -> str:
    article_html = [_render_block_html(block) for block in document.content]
    comments_html = [_render_comment(comment) for comment in document.comments]
    return _TEMPLATE.render(
        title=document.metadata.title,
        article_html=article_html,
        comments_html=comments_html,
        include_comments=include_comments,
    )


def _render_comment(comment: Comment) -> dict[str, str | list[str]]:
    author = comment.author.name if comment.author is not None else "Unknown"
    return {
        "author": author,
        "body": [_render_block_html(block) for block in comment.body],
    }


def _render_block_html(block: ContentBlock) -> str:
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
        return f'<img src="{escape(str(block.url))}"{caption}>'
    return f"<p>{escape(block.text or '')}</p>"
