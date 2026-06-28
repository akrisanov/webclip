from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from webclip.registry import AdapterRegistry

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
    console.print("[yellow]Not implemented yet:[/yellow] save pipeline")
    console.print(
        {
            "url": url,
            "format": output_format,
            "with_comments": with_comments,
            "vault": str(vault) if vault else None,
            "directory": directory,
        }
    )
    raise typer.Exit(code=1)


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
    console.print("[yellow]Not implemented yet:[/yellow] inspect pipeline")
    console.print({"url": url})
    raise typer.Exit(code=1)


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


if __name__ == "__main__":
    app()
