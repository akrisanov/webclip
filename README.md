# webclip

Extensible CLI for saving web pages, comments, and assets into Obsidian-friendly archives.

## Quick start

```bash
uv venv
uv sync
uv run webclip --help
```

## Common commands

Using Make:

```bash
make check
```

Using just:

```bash
just check
```

## Browser auth and authenticated fetch

```bash
uv run webclip auth vas3k
uv run webclip save "https://vas3k.club/post/1941225/" --fetcher browser --auth-site vas3k
uv run webclip save "https://example.org" --format md,json,html,pdf
uv run webclip update ./Clippings/example.org/example-domain --mode append --dry-run
```
