from pathlib import Path

from pydantic import HttpUrl, TypeAdapter
from pytest import MonkeyPatch
from typer.testing import CliRunner

from webclip.cli import app

runner = CliRunner()
HTTP_URL = TypeAdapter(HttpUrl)


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "web clipping CLI" in result.stdout


def test_adapters_list() -> None:
    result = runner.invoke(app, ["adapters", "list"])
    assert result.exit_code == 0
    assert "vas3k" in result.stdout
    assert "generic" in result.stdout


def test_save_rejects_unsupported_format() -> None:
    result = runner.invoke(app, ["save", "https://example.org", "--format", "pdf"])
    assert result.exit_code == 2


def test_save_writes_report_with_mocked_service(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    from datetime import UTC, datetime

    from webclip.models import Document, ExtractionMetadata, Metadata
    from webclip.outputs.filesystem import WriteResult
    from webclip.service import SaveResult, WebclipService

    async def fake_save(
        self,
        url: str,
        output_formats: set[str],
        base_dir: Path,
        directory_template: str,
        include_comments: bool,
    ) -> SaveResult:
        output_dir = base_dir / "Clippings" / "example.org" / "test"
        return SaveResult(
            document=Document(
                doc_id="id",
                slug="test",
                metadata=Metadata(
                    site="example.org",
                    title="T",
                    source_url=HTTP_URL.validate_python(url),
                ),
                extraction=ExtractionMetadata(
                    adapter_name="generic",
                    fetcher_name="http",
                    extracted_at=datetime.now(UTC),
                ),
            ),
            output=WriteResult(output_dir=output_dir, written_files=[output_dir / "index.md"]),
        )

    monkeypatch.setattr(WebclipService, "save", fake_save)
    result = runner.invoke(app, ["save", "https://example.org", "--vault", str(tmp_path)])
    assert result.exit_code == 0
    assert "Saved:" in result.stdout
