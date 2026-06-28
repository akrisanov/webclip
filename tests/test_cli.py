from pathlib import Path

from pydantic import HttpUrl, TypeAdapter
from pytest import MonkeyPatch
from typer.testing import CliRunner

from webclip.cli import app
from webclip.diagnostics import CheckResult
from webclip.service import UpdateResult

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
    result = runner.invoke(app, ["save", "https://example.org", "--format", "xml"])
    assert result.exit_code == 2


def test_save_rejects_unsupported_fetcher() -> None:
    result = runner.invoke(app, ["save", "https://example.org", "--fetcher", "playwright"])
    assert result.exit_code == 2


def test_save_rejects_unsupported_theme() -> None:
    result = runner.invoke(app, ["save", "https://example.org", "--theme", "retro"])
    assert result.exit_code == 2


def test_update_rejects_unsupported_mode() -> None:
    result = runner.invoke(app, ["update", "/tmp/archive", "--mode", "invalid"])
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
        use_obsidian_output: bool = False,
        theme: str = "readable",
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


def test_auth_uses_profile_and_known_login_url(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_auth(site: str, login_url: str, profile_dir: Path) -> None:
        captured["site"] = site
        captured["login_url"] = login_url
        captured["profile_dir"] = str(profile_dir)

    monkeypatch.setattr("webclip.cli.run_auth_session", fake_auth)
    result = runner.invoke(app, ["auth", "vas3k"])

    assert result.exit_code == 0
    assert captured["site"] == "vas3k"
    assert captured["login_url"] == "https://vas3k.club/auth/login/"
    assert "profiles/vas3k" in captured["profile_dir"]


def test_doctor_reports_results(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "webclip.cli.run_doctor",
        lambda vault: [
            CheckResult(name="Python version", ok=True, details="3.14"),
            CheckResult(name="Playwright Chromium", ok=False, details="missing"),
        ],
    )
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "Playwright Chromium" in result.stdout


def test_update_reports_planned_files(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    async def fake_update(
        self,
        archive_path: Path,
        mode: str,
        dry_run: bool = False,
        theme: str = "readable",
    ) -> UpdateResult:
        return UpdateResult(
            mode=mode,
            source_url="https://example.org/post",
            target_dir=archive_path,
            dry_run=dry_run,
            files=[archive_path / "index.md", archive_path / "source.json"],
            added_comments=2,
        )

    monkeypatch.setattr("webclip.cli.WebclipService.update", fake_update)
    result = runner.invoke(
        app,
        ["update", str(tmp_path), "--mode", "append", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Planned files" in result.stdout
    assert "Added comments: 2" in result.stdout


def test_render_from_source_json_writes_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    from datetime import UTC, datetime

    from webclip.models import Document, ExtractionMetadata, Metadata

    source_json = tmp_path / "source.json"
    source_json.write_text(
        Document(
            doc_id="id",
            slug="sample",
            metadata=Metadata(
                site="example.org",
                title="Example",
                source_url=HTTP_URL.validate_python("https://example.org/post"),
            ),
            extraction=ExtractionMetadata(
                adapter_name="generic",
                fetcher_name="http",
                extracted_at=datetime.now(UTC),
            ),
        ).model_dump_json(indent=2, exclude_none=True),
        encoding="utf-8",
    )

    async def fake_render_document(
        self,
        document: Document,
        output_formats: set[str],
        include_comments: bool = True,
        theme: str = "readable",
        asset_url_map: dict[str, str] | None = None,
        base_href: str | None = None,
    ) -> dict[str, str | bytes]:
        return {"index.md": "# Rendered\n", "source.json": "{}\n"}

    monkeypatch.setattr("webclip.cli.WebclipService.render_document", fake_render_document)
    out_dir = tmp_path / "rendered"
    result = runner.invoke(
        app,
        ["render", str(source_json), "--format", "md,json", "--output-dir", str(out_dir)],
    )
    assert result.exit_code == 0
    assert (out_dir / "index.md").exists()
    assert "Rendered:" in result.stdout
