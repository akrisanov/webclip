from datetime import UTC, datetime
from pathlib import Path

from pydantic import HttpUrl, TypeAdapter

from webclip.models import BlockType, Comment, ContentBlock, Document, ExtractionMetadata, Metadata
from webclip.outputs.filesystem import FilesystemOutput
from webclip.outputs.obsidian import ObsidianOutput
from webclip.renderers.html_renderer import render_html
from webclip.renderers.markdown import render_markdown

HTTP_URL = TypeAdapter(HttpUrl)


def _sample_document() -> Document:
    return Document(
        doc_id="doc1",
        slug="sample",
        metadata=Metadata(
            site="example.org",
            title="Sample Title",
            source_url=HTTP_URL.validate_python("https://example.org/post"),
        ),
        content=[
            ContentBlock(type=BlockType.heading, text="Оглавление", level=1),
            ContentBlock(type=BlockType.heading, text="Heading", level=2),
            ContentBlock(type=BlockType.heading, text="Subheading", level=3),
            ContentBlock(type=BlockType.paragraph, text="[Назад к оглавлению](#oglavlenie)"),
            ContentBlock(
                type=BlockType.paragraph,
                text="Paragraph with [link](https://example.org/docs)",
            ),
            ContentBlock(type=BlockType.list, text="- Item one\n- Item two"),
            ContentBlock(
                type=BlockType.image,
                url=HTTP_URL.validate_python("https://example.org/img.png"),
                caption="image",
            ),
        ],
        comments=[
            Comment(
                comment_id="c1",
                body=[ContentBlock(type=BlockType.paragraph, text="Top comment")],
            ),
            Comment(
                comment_id="c2",
                parent_id="c1",
                body=[ContentBlock(type=BlockType.paragraph, text="Reply comment")],
            ),
        ],
        extraction=ExtractionMetadata(
            adapter_name="generic",
            fetcher_name="http",
            extracted_at=datetime.now(UTC),
        ),
    )


def test_render_html_contains_title_and_sections() -> None:
    html = render_html(_sample_document(), include_comments=True)
    assert "<h1>Sample Title</h1>" in html
    assert "<h2>Contents</h2>" in html
    assert "<h2>Article</h2>" in html
    assert '<h2 id="heading">Heading</h2>' in html
    assert '<h3 id="subheading">Subheading</h3>' in html
    assert 'class="toc-level-3"' in html
    assert 'href="#subheading">Subheading</a>' in html
    assert 'href="https://example.org/docs"' in html
    assert "<ul><li>Item one</li><li>Item two</li></ul>" in html
    assert "Назад к оглавлению" not in html
    assert 'class="theme-readable"' in html
    assert 'aria-label="Quick navigation"' in html
    assert "comment-card" in html
    assert "comment-level-1" in html


def test_render_html_applies_theme() -> None:
    html = render_html(_sample_document(), include_comments=True, theme="serif")
    assert 'class="theme-serif"' in html


def test_render_html_renders_inline_markdown_styles() -> None:
    document = _sample_document().model_copy(deep=True)
    document.content.append(
        ContentBlock(
            type=BlockType.list,
            text="- **necesito este** - мне нужно это\n- *hablas ingles?* - говоришь по-английски?",
        )
    )
    html = render_html(document, include_comments=False)
    assert "<strong>necesito este</strong>" in html
    assert "<em>hablas ingles?</em>" in html


def test_render_html_uses_ru_lang_for_cyrillic_document() -> None:
    document = _sample_document().model_copy(deep=True)
    document.metadata.title = "Русский заголовок"
    html = render_html(document, include_comments=False)
    assert '<html lang="ru">' in html


def test_render_html_dedupes_adjacent_list_items_and_autolinks_plain_urls() -> None:
    document = _sample_document().model_copy(deep=True)
    document.content.append(
        ContentBlock(
            type=BlockType.list,
            text=(
                "- Один пункт\n"
                "- Ссылка https://example.org/really/long/path/value\n"
                "- Один пункт\n"
                "- [https://example.org/really/long/path/value](https://example.org/really/long/path/value)"
            ),
        )
    )
    html = render_html(document, include_comments=False)
    assert html.count("<li>Один пункт</li>") == 1
    assert 'href="https://example.org/really/long/path/value"' in html
    assert "example.org/really/long/path/value" in html


def test_render_markdown_replaces_source_toc_with_normalized_contents() -> None:
    markdown = render_markdown(_sample_document(), include_comments=False)
    assert "## Contents" in markdown
    assert "- [Heading](#heading)" in markdown
    assert "  - [Subheading](#subheading)" in markdown
    assert "# Оглавление" not in markdown
    assert "Назад к оглавлению" not in markdown


def test_render_markdown_uses_obsidian_style_anchors() -> None:
    document = _sample_document().model_copy(deep=True)
    document.content.extend(
        [
            ContentBlock(type=BlockType.heading, text="Раздел Язык", level=3),
            ContentBlock(type=BlockType.heading, text="Раздел Язык", level=3),
            ContentBlock(
                type=BlockType.paragraph,
                text="[Перейти](#Раздел Язык)",
            ),
        ]
    )
    markdown = render_markdown(document, include_comments=False)
    assert "- [Раздел Язык](#раздел-язык)" in markdown
    assert "- [Раздел Язык](#раздел-язык-1)" in markdown
    assert "[Перейти](#раздел-язык)" in markdown


def test_filesystem_output_writes_text_and_binary(tmp_path: Path) -> None:
    writer = FilesystemOutput(tmp_path)
    result = writer.write(
        document=_sample_document(),
        directory_template="Clippings/{site}/{slug}",
        artifacts={"index.md": "# Hello\n", "article.pdf": b"%PDF-1.4"},
    )
    index = result.output_dir / "index.md"
    pdf = result.output_dir / "article.pdf"
    assert index.read_text(encoding="utf-8") == "# Hello\n"
    assert pdf.read_bytes() == b"%PDF-1.4"


def test_obsidian_output_creates_notes_once(tmp_path: Path) -> None:
    writer = ObsidianOutput(tmp_path)
    document = _sample_document()
    result = writer.write(
        document=document,
        directory_template="Clippings/{site}/{slug}",
        artifacts={"index.md": "# One\n"},
    )
    notes = result.output_dir / "notes.md"
    assert notes.exists()
    notes.write_text("## My notes\n\nCustom text\n", encoding="utf-8")

    writer.write(
        document=document,
        directory_template="Clippings/{site}/{slug}",
        artifacts={"index.md": "# Two\n"},
    )
    assert notes.read_text(encoding="utf-8") == "## My notes\n\nCustom text\n"
