from __future__ import annotations

import asyncio
from json import loads
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from webclip.auth import profile_dir_for_site, resolve_login_url, run_auth_session
from webclip.diagnostics import run_doctor
from webclip.models import Document
from webclip.outputs.filesystem import FilesystemOutput
from webclip.registry import AdapterRegistry
from webclip.renderers.html_renderer import SUPPORTED_THEMES
from webclip.service import (
    SUPPORTED_FETCHERS,
    SUPPORTED_FORMATS,
    SUPPORTED_UPDATE_MODES,
    WebclipService,
)

app = typer.Typer(help="Extensible web clipping CLI for Obsidian")
adapters_app = typer.Typer(help="Manage and inspect registered adapters")
app.add_typer(adapters_app, name="adapters")
console = Console()


@app.command()
def save(
    url: str,
    output_format: Annotated[str, typer.Option("--format")] = "md",
    fetcher: Annotated[str, typer.Option("--fetcher")] = "http",
    with_comments: Annotated[bool, typer.Option("--with-comments")] = True,
    theme: Annotated[str, typer.Option("--theme")] = "readable",
    vault: Annotated[Path | None, typer.Option("--vault")] = None,
    directory: Annotated[str | None, typer.Option("--directory")] = None,
    auth_site: Annotated[str | None, typer.Option("--auth-site")] = None,
) -> None:
    formats = _parse_formats(output_format)
    fetcher_kind = _parse_fetcher(fetcher)
    rendered_theme = _parse_theme(theme)
    base_dir = vault or Path.cwd()
    directory_template = directory or "Clippings/{site}/{slug}"
    profile_dir = profile_dir_for_site(auth_site) if auth_site else None
    service = WebclipService(fetcher_kind=fetcher_kind, profile_dir=profile_dir)
    result = asyncio.run(
        service.save(
            url=url,
            output_formats=formats,
            base_dir=base_dir,
            directory_template=directory_template,
            include_comments=with_comments,
            use_obsidian_output=vault is not None,
            theme=rendered_theme,
        )
    )
    console.print(f"[green]Saved:[/green] {result.output.output_dir}")
    for file_path in result.output.written_files:
        console.print(f"  - {file_path}")


@app.command()
def update(
    archive_path: Path,
    mode: Annotated[str, typer.Option("--mode")] = "merge",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    theme: Annotated[str, typer.Option("--theme")] = "readable",
    fetcher: Annotated[str, typer.Option("--fetcher")] = "http",
    auth_site: Annotated[str | None, typer.Option("--auth-site")] = None,
) -> None:
    update_mode = _parse_update_mode(mode)
    fetcher_kind = _parse_fetcher(fetcher)
    rendered_theme = _parse_theme(theme)
    profile_dir = profile_dir_for_site(auth_site) if auth_site else None
    service = WebclipService(fetcher_kind=fetcher_kind, profile_dir=profile_dir)
    result = asyncio.run(
        service.update(
            archive_path=archive_path,
            mode=update_mode,
            dry_run=dry_run,
            theme=rendered_theme,
        )
    )
    action = "Planned files" if dry_run else "Updated files"
    console.print(f"{action}:")
    for file_path in result.files:
        console.print(f"  - {file_path}")
    console.print(f"Added comments: {result.added_comments}")


@app.command()
def inspect(
    url: str,
    fetcher: Annotated[str, typer.Option("--fetcher")] = "http",
    auth_site: Annotated[str | None, typer.Option("--auth-site")] = None,
) -> None:
    fetcher_kind = _parse_fetcher(fetcher)
    profile_dir = profile_dir_for_site(auth_site) if auth_site else None
    service = WebclipService(fetcher_kind=fetcher_kind, profile_dir=profile_dir)
    result = asyncio.run(service.inspect(url))
    console.print(f"Matched adapter: {result.adapter_name}")
    console.print(f"Fetcher: {result.fetcher_name}")
    console.print(f"Title: {result.title}")
    console.print(f"Article blocks: {result.article_blocks}")
    console.print(f"Comments: {result.comments}")
    console.print(f"Images: {result.images}")
    console.print(f"Nested comment depth: {result.nested_comment_depth}")
    console.print(f"Authentication: {'yes' if result.authentication_required else 'no'}")


@app.command()
def auth(
    site: str,
    login_url: Annotated[str | None, typer.Option("--login-url")] = None,
) -> None:
    resolved_login_url = resolve_login_url(site, login_url)
    profile_dir = profile_dir_for_site(site)
    console.print(f"Profile: {profile_dir}")
    console.print(f"Opening: {resolved_login_url}")
    run_auth_session(site=site, login_url=resolved_login_url, profile_dir=profile_dir)
    console.print("[green]Authentication profile saved.[/green]")


@app.command()
def render(
    source: Path,
    output_format: Annotated[str, typer.Option("--format")] = "md",
    output_dir: Annotated[Path | None, typer.Option("--output-dir")] = None,
    with_comments: Annotated[bool, typer.Option("--with-comments")] = True,
    theme: Annotated[str, typer.Option("--theme")] = "readable",
) -> None:
    formats = _parse_formats(output_format)
    rendered_theme = _parse_theme(theme)
    source_json, default_output_dir = _resolve_render_source(source)
    document = Document.model_validate(loads(source_json.read_text(encoding="utf-8")))
    target_dir = output_dir or default_output_dir

    service = WebclipService()
    artifacts = asyncio.run(
        service.render_document(
            document=document,
            output_formats=formats,
            include_comments=with_comments,
            theme=rendered_theme,
        )
    )
    writer = FilesystemOutput(Path.cwd())
    result = writer.write_to_directory(target_dir, artifacts)
    console.print(f"[green]Rendered:[/green] {result.output_dir}")
    for file_path in result.written_files:
        console.print(f"  - {file_path}")


@adapters_app.command("list")
def adapters_list() -> None:
    registry = AdapterRegistry()
    table = Table(title="Registered adapters")
    table.add_column("Name")
    table.add_column("Source")
    table.add_column("Description")
    for adapter in registry.list_adapters():
        table.add_row(adapter.name, adapter.source, adapter.description)
    console.print(table)


@app.command()
def doctor(vault: Annotated[Path | None, typer.Option("--vault")] = None) -> None:
    results = run_doctor(vault=vault)
    table = Table(title="webclip doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    has_failures = False
    for result in results:
        status = "[green]OK[/green]" if result.ok else "[red]FAIL[/red]"
        if not result.ok:
            has_failures = True
        table.add_row(result.name, status, result.details)
    console.print(table)
    if has_failures:
        raise typer.Exit(code=1)


def _parse_formats(raw_value: str) -> set[str]:
    formats = {entry.strip().lower() for entry in raw_value.split(",") if entry.strip()}
    if not formats:
        raise typer.BadParameter("At least one format must be provided via --format")
    unsupported = formats - SUPPORTED_FORMATS
    if unsupported:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        unsupported_values = ", ".join(sorted(unsupported))
        raise typer.BadParameter(
            f"Unsupported format(s): {unsupported_values}. Supported: {supported}"
        )
    return formats


def _parse_fetcher(raw_value: str) -> str:
    fetcher_kind = raw_value.strip().lower()
    if fetcher_kind not in SUPPORTED_FETCHERS:
        supported = ", ".join(sorted(SUPPORTED_FETCHERS))
        raise typer.BadParameter(
            f"Unsupported fetcher: {fetcher_kind}. Supported: {supported}"
        )
    return fetcher_kind


def _parse_update_mode(raw_value: str) -> str:
    update_mode = raw_value.strip().lower()
    if update_mode not in SUPPORTED_UPDATE_MODES:
        supported = ", ".join(sorted(SUPPORTED_UPDATE_MODES))
        raise typer.BadParameter(
            f"Unsupported update mode: {update_mode}. Supported: {supported}"
        )
    return update_mode


def _parse_theme(raw_value: str) -> str:
    theme = raw_value.strip().lower()
    if theme not in SUPPORTED_THEMES:
        supported = ", ".join(sorted(SUPPORTED_THEMES))
        raise typer.BadParameter(f"Unsupported theme: {theme}. Supported: {supported}")
    return theme


def _resolve_render_source(source: Path) -> tuple[Path, Path]:
    if source.exists() and source.is_file():
        return source, source.parent
    source_json = source / "source.json"
    if source_json.exists():
        return source_json, source
    msg = f"Expected source.json at: {source_json}"
    raise typer.BadParameter(msg)


if __name__ == "__main__":
    app()
