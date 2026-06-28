from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from webclip.registry import AdapterRegistry
from webclip.service import SUPPORTED_FORMATS, WebclipService

app = typer.Typer(help="Extensible web clipping CLI for Obsidian")
adapters_app = typer.Typer(help="Manage and inspect registered adapters")
app.add_typer(adapters_app, name="adapters")
console = Console()


@app.command()
def save(
    url: str,
    output_format: Annotated[str, typer.Option("--format")] = "md",
    with_comments: Annotated[bool, typer.Option("--with-comments")] = True,
    vault: Annotated[Path | None, typer.Option("--vault")] = None,
    directory: Annotated[str | None, typer.Option("--directory")] = None,
) -> None:
    formats = _parse_formats(output_format)
    base_dir = vault or Path.cwd()
    directory_template = directory or "Clippings/{site}/{slug}"
    service = WebclipService()
    result = asyncio.run(
        service.save(
            url=url,
            output_formats=formats,
            base_dir=base_dir,
            directory_template=directory_template,
            include_comments=with_comments,
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
) -> None:
    console.print("[yellow]Not implemented yet:[/yellow] update pipeline")
    console.print({"archive_path": str(archive_path), "mode": mode, "dry_run": dry_run})
    raise typer.Exit(code=1)


@app.command()
def inspect(url: str) -> None:
    service = WebclipService()
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
def auth(site: str) -> None:
    console.print("[yellow]Not implemented yet:[/yellow] auth flow")
    console.print({"site": site})
    raise typer.Exit(code=1)


@app.command()
def render(source: Path, output_format: Annotated[str, typer.Option("--format")] = "md") -> None:
    console.print("[yellow]Not implemented yet:[/yellow] render pipeline")
    console.print({"source": str(source), "format": output_format})
    raise typer.Exit(code=1)


@adapters_app.command("list")
def adapters_list() -> None:
    registry = AdapterRegistry()
    table = Table(title="Registered adapters")
    table.add_column("Name")
    table.add_column("Description")
    for adapter in registry.list_adapters():
        table.add_row(adapter.name, adapter.description)
    console.print(table)


@app.command()
def doctor() -> None:
    console.print("[yellow]Not implemented yet:[/yellow] environment diagnostics")
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


if __name__ == "__main__":
    app()
