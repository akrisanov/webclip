from datetime import UTC, datetime
from pathlib import Path

from pydantic import HttpUrl, TypeAdapter

from webclip.models import BlockType, ContentBlock, Document, ExtractionMetadata, Metadata
from webclip.outputs.filesystem import FilesystemOutput
from webclip.renderers.html_renderer import render_html

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
            ContentBlock(type=BlockType.heading, text="Heading", level=2),
            ContentBlock(type=BlockType.paragraph, text="Paragraph"),
            ContentBlock(
                type=BlockType.image,
                url=HTTP_URL.validate_python("https://example.org/img.png"),
                caption="image",
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
    assert "<h2>Article</h2>" in html
    assert "Paragraph" in html


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
