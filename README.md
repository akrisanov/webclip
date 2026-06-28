# webclip

`webclip` — CLI для сохранения веб-страниц (контент, комментарии, изображения) в локальный архив или Obsidian.

## Установка

```bash
uv venv
uv sync
uv run playwright install chromium
```

## Быстрый старт

Сохранить страницу в Markdown + JSON:

```bash
uv run webclip save "https://example.org" --format md,json
```

Сохранить в Obsidian Vault:

```bash
uv run webclip save "https://example.org" --vault "/path/to/YourVault"
```

Проверить извлечение:

```bash
uv run webclip inspect "https://example.org"
```

## Авторизация (для закрытых страниц)

```bash
uv run webclip auth vas3k
uv run webclip save "https://vas3k.club/post/1941225/" --fetcher browser --auth-site vas3k
```

## Обновление сохранённого архива

```bash
uv run webclip update ./Clippings/example.org/example-domain --mode append
uv run webclip update ./Clippings/example.org/example-domain --mode merge --dry-run
```

Режимы:
- `append` — добавить только новые комментарии;
- `merge` — обновить текущие артефакты;
- `replace` — полностью пересоздать сгенерированные файлы.

## Полезные команды

```bash
uv run webclip adapters list
uv run webclip doctor
uv run webclip --help
```
