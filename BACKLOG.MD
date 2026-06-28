# BACKLOG

## Stage 1 — Project bootstrap

- [x] Initialize Python project metadata and packaging.
- [x] Add core CLI command tree (`save`, `update`, `inspect`, `auth`, `render`, `adapters`, `doctor`).
- [x] Add base architecture modules (`config`, `models`, `registry`, `exceptions`, `logging`).
- [x] Configure developer tooling (`uv`, `ruff`, `ty`, `pytest`).
- [x] Add first end-to-end `save` pipeline implementation.

## Stage 2 — Fetch and extraction

- [x] Implement HTTP fetcher.
- [x] Implement Playwright fetcher with persistent auth profile.
- [x] Implement generic adapter.
- [x] Implement `vas3k.club` adapter for article/comments/assets extraction.

## Stage 3 — Rendering and outputs

- [x] Implement Markdown renderer.
- [x] Implement JSON renderer.
- [x] Implement HTML renderer.
- [x] Implement PDF renderer (via Playwright print).
- [x] Implement filesystem output target.
- [x] Implement filesystem and Obsidian output targets.

## Stage 4 — Update and plugin architecture

- [x] Implement update modes (`append`, `merge`, `replace`) with `--dry-run`.
- [ ] Preserve user notes on update.
- [ ] Add plugin discovery via entry points.
- [ ] Add declarative adapter loading.
