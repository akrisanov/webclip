from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import HttpUrl, TypeAdapter
from pytest import MonkeyPatch

from webclip.exceptions import AssetFetchError
from webclip.models import Asset, BlockType, ContentBlock, Document, ExtractionMetadata, Metadata
from webclip.service import WebclipService

HTTP_URL = TypeAdapter(HttpUrl)


def _image_document() -> Document:
    image_url = "https://cdn.example.org/image.png"
    return Document(
        doc_id="doc-asset",
        slug="asset-test",
        metadata=Metadata(
            site="example.org",
            title="Asset test",
            source_url=HTTP_URL.validate_python("https://example.org/post/1"),
        ),
        content=[
            ContentBlock(
                type=BlockType.image,
                url=HTTP_URL.validate_python(image_url),
                caption="example",
            )
        ],
        assets=[Asset(source_url=HTTP_URL.validate_python(image_url))],
        extraction=ExtractionMetadata(
            adapter_name="generic",
            fetcher_name="http",
            extracted_at=datetime.now(UTC),
        ),
    )


@pytest.mark.asyncio
async def test_save_downloads_assets_and_localizes_links(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_extract(self, url: str) -> Document:
        return _image_document()

    async def fake_fetch_asset(self, url: str) -> tuple[bytes, str | None]:
        return (b"PNGDATA", "image/png")

    monkeypatch.setattr(WebclipService, "extract", fake_extract)
    monkeypatch.setattr(WebclipService, "_fetch_asset", fake_fetch_asset)

    service = WebclipService(fetcher_kind="http")
    result = await service.save(
        url="https://example.org/post/1",
        output_formats={"md", "json", "html"},
        base_dir=tmp_path,
        directory_template="Clippings/{site}/{slug}",
        include_comments=True,
    )

    output_dir = result.output.output_dir
    assert (output_dir / "assets" / "asset-001.png").read_bytes() == b"PNGDATA"
    markdown = (output_dir / "index.md").read_text(encoding="utf-8")
    html = (output_dir / "print.html").read_text(encoding="utf-8")
    source_json = (output_dir / "source.json").read_text(encoding="utf-8")
    assert "assets/asset-001.png" in markdown
    assert 'src="assets/asset-001.png"' in html
    assert '"local_path": "assets/asset-001.png"' in source_json


@pytest.mark.asyncio
async def test_save_reports_failed_assets_and_continues(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_extract(self, url: str) -> Document:
        return _image_document()

    async def failing_fetch_asset(self, url: str) -> tuple[bytes, str | None]:
        raise AssetFetchError("boom")

    monkeypatch.setattr(WebclipService, "extract", fake_extract)
    monkeypatch.setattr(WebclipService, "_fetch_asset", failing_fetch_asset)

    service = WebclipService(fetcher_kind="http", asset_continue_on_error=True)
    result = await service.save(
        url="https://example.org/post/1",
        output_formats={"md", "json"},
        base_dir=tmp_path,
        directory_template="Clippings/{site}/{slug}",
        include_comments=True,
    )

    assert result.downloaded_assets == 0
    assert result.failed_assets == ["https://cdn.example.org/image.png"]
    markdown = (result.output.output_dir / "index.md").read_text(encoding="utf-8")
    assert "https://cdn.example.org/image.png" in markdown
