# BACKLOG

## Stage 1 — Project bootstrap

- [x] Initialize Python project metadata and packaging.
- [x] Add core CLI command tree (`save`, `update`, `inspect`, `auth`, `render`, `adapters`, `doctor`).
- [x] Add base architecture modules (`config`, `models`, `registry`, `exceptions`, `logging`).
- [x] Configure developer tooling (`uv`, `ruff`, `ty`, `pytest`).
- [ ] Add first end-to-end `save` pipeline implementation.

## Stage 2 — Fetch and extraction

- [ ] Implement HTTP fetcher.
- [ ] Implement Playwright fetcher with persistent auth profile.
- [ ] Implement generic adapter.
- [ ] Implement `vas3k.club` adapter for article/comments/assets extraction.

## Stage 3 — Rendering and outputs

- [ ] Implement Markdown renderer.
- [ ] Implement JSON renderer.
- [ ] Implement HTML renderer.
- [ ] Implement PDF renderer (via Playwright print).
- [ ] Implement filesystem and Obsidian output targets.

## Stage 4 — Update and plugin architecture

- [ ] Implement update modes (`append`, `merge`, `replace`) with `--dry-run`.
- [ ] Preserve user notes on update.
- [ ] Add plugin discovery via entry points.
- [ ] Add declarative adapter loading.

