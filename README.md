# webclip

`webclip` is a CLI for saving web pages (content, comments, and images) into a local archive or an Obsidian vault.

## Installation

```bash
uv venv
uv sync
uv run playwright install chromium
```

## Quick start

Save a page as Markdown + JSON:

```bash
uv run webclip save "https://example.org" --format md,json
```

Save directly into an Obsidian vault:

```bash
uv run webclip save "https://example.org" --vault "/path/to/YourVault"
```

Inspect extraction results:

```bash
uv run webclip inspect "https://example.org"
```

## Authentication (for protected pages)

```bash
uv run webclip auth vas3k
uv run webclip save "https://vas3k.club/post/1941225/" --fetcher browser --auth-site vas3k
```

## Update an existing archive

```bash
uv run webclip update ./Clippings/example.org/example-domain --mode append
uv run webclip update ./Clippings/example.org/example-domain --mode merge --dry-run
```

Modes:

- `append` — add only new comments.
- `merge` — regenerate current output files from the latest source.
- `replace` — fully recreate generated files.

## Useful commands

```bash
uv run webclip adapters list
uv run webclip doctor
uv run webclip --help
```
