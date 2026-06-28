from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import HttpUrl, TypeAdapter
from pytest import MonkeyPatch

from webclip.models import Comment, Document, ExtractionMetadata, Metadata
from webclip.service import WebclipService

HTTP_URL = TypeAdapter(HttpUrl)


def _document(comment_ids: list[str]) -> Document:
    return Document(
        doc_id="doc1",
        slug="sample",
        metadata=Metadata(
            site="example.org",
            title="Sample",
            source_url=HTTP_URL.validate_python("https://example.org/post"),
        ),
        comments=[Comment(comment_id=comment_id) for comment_id in comment_ids],
        extraction=ExtractionMetadata(
            adapter_name="generic",
            fetcher_name="http",
            extracted_at=datetime.now(UTC),
        ),
    )


@pytest.mark.asyncio
async def test_update_append_adds_only_new_comments(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir(parents=True)
    (archive / "index.md").write_text("# Existing\n", encoding="utf-8")
    (archive / "source.json").write_text(
        _document(["c1"]).model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    async def fake_extract(self, url: str) -> Document:
        return _document(["c1", "c2"])

    monkeypatch.setattr(WebclipService, "extract", fake_extract)
    service = WebclipService(fetcher_kind="http")
    result = await service.update(archive_path=archive, mode="append", dry_run=False)

    assert result.added_comments == 1
    updated = Document.model_validate_json((archive / "source.json").read_text(encoding="utf-8"))
    assert [comment.comment_id for comment in updated.comments] == ["c1", "c2"]


@pytest.mark.asyncio
async def test_update_replace_preserves_notes_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir(parents=True)
    (archive / "index.md").write_text("# Existing\n", encoding="utf-8")
    (archive / "source.json").write_text(
        _document(["c1"]).model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )
    notes = archive / "notes.md"
    notes.write_text("## My notes\n\nDo not overwrite\n", encoding="utf-8")

    async def fake_extract(self, url: str) -> Document:
        return _document(["c2"])

    monkeypatch.setattr(WebclipService, "extract", fake_extract)
    service = WebclipService(fetcher_kind="http")
    await service.update(archive_path=archive, mode="replace", dry_run=False)

    assert notes.read_text(encoding="utf-8") == "## My notes\n\nDo not overwrite\n"
