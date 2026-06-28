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

Save with book-style HTML/PDF typography theme:

```bash
uv run webclip save "https://example.org" --format html,pdf --theme serif
```

Save directly into an Obsidian vault:

```bash
uv run webclip save "https://example.org" --vault "/path/to/YourVault"
```

How it works:

- `--vault` sets the base directory to your vault path.
- Output is written under `Clippings/{site}/{slug}` by default.
- You can override this layout with `--directory`, for example:

```bash
uv run webclip save "https://example.org/post/1" \
  --vault "/path/to/YourVault" \
  --directory "WebClips/{site}/{slug}"
```

Default output structure:

```text
<vault>/
└── Clippings/
    └── <site>/
        └── <slug>/
            ├── index.md
            ├── source.json
            ├── print.html        # when --format includes html
            ├── article.pdf       # when --format includes pdf
            ├── assets/
            │   └── asset-001.png
            └── notes.md
```

Notes:

- `notes.md` is created automatically for Obsidian flow.
- On `update`, generated files are refreshed according to mode, while `notes.md` is preserved.
- Image assets are downloaded into `assets/`, and links in Markdown/HTML/PDF are localized.

Inspect extraction results:

```bash
uv run webclip inspect "https://example.org"
```

Re-render from an existing `source.json` archive:

```bash
uv run webclip render ./Clippings/example.org/example-domain/source.json \
  --format md,html,pdf \
  --theme serif \
  --output-dir ./Clippings/example.org/example-domain
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

Themes (`--theme` for `save`/`update`): `readable`, `serif`, `dark`.

## Useful commands

```bash
uv run webclip adapters list
uv run webclip doctor
uv run webclip --help
```
