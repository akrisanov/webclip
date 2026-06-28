from __future__ import annotations

from dataclasses import dataclass
from json import loads
from pathlib import Path

from webclip.fetchers.base import Fetcher, FetchRequest
from webclip.fetchers.http import HttpFetcher
from webclip.fetchers.playwright import PlaywrightFetcher
from webclip.models import Asset, Document
from webclip.outputs.filesystem import FilesystemOutput, WriteResult
from webclip.outputs.obsidian import ObsidianOutput
from webclip.registry import AdapterRegistry
from webclip.renderers.html_renderer import render_html
from webclip.renderers.json_renderer import render_document_json
from webclip.renderers.markdown import render_markdown
from webclip.renderers.pdf_renderer import render_pdf_bytes

SUPPORTED_FORMATS = {"md", "json", "html", "pdf"}
SUPPORTED_FETCHERS = {"http", "browser"}
SUPPORTED_UPDATE_MODES = {"append", "merge", "replace"}


@dataclass(frozen=True)
class SaveResult:
    document: Document
    output: WriteResult


@dataclass(frozen=True)
class InspectResult:
    adapter_name: str
    fetcher_name: str
    title: str
    article_blocks: int
    comments: int
    images: int
    nested_comment_depth: int
    authentication_required: bool


@dataclass(frozen=True)
class UpdateResult:
    mode: str
    source_url: str
    target_dir: Path
    dry_run: bool
    files: list[Path]
    added_comments: int


class WebclipService:
    def __init__(
        self,
        registry: AdapterRegistry | None = None,
        fetcher_kind: str = "http",
        profile_dir: Path | None = None,
    ) -> None:
        self.registry = registry or AdapterRegistry()
        self.fetcher = self._build_fetcher(fetcher_kind=fetcher_kind, profile_dir=profile_dir)
        self.fetcher_kind = fetcher_kind

    async def save(
        self,
        url: str,
        output_formats: set[str],
        base_dir: Path,
        directory_template: str,
        include_comments: bool,
        use_obsidian_output: bool = False,
    ) -> SaveResult:
        unsupported = output_formats - SUPPORTED_FORMATS
        if unsupported:
            msg = f"Unsupported output format(s): {', '.join(sorted(unsupported))}"
            raise ValueError(msg)

        document = await self.extract(url)
        artifacts = await self._build_artifacts(
            document=document,
            output_formats=output_formats,
            include_comments=include_comments,
        )

        writer = ObsidianOutput(base_dir) if use_obsidian_output else FilesystemOutput(base_dir)
        output = writer.write(
            document=document,
            directory_template=directory_template,
            artifacts=artifacts,
        )
        return SaveResult(document=document, output=output)

    async def update(
        self,
        archive_path: Path,
        mode: str,
        dry_run: bool = False,
    ) -> UpdateResult:
        if mode not in SUPPORTED_UPDATE_MODES:
            msg = f"Unsupported update mode '{mode}'"
            raise ValueError(msg)

        source_path = archive_path / "source.json"
        if not source_path.exists():
            msg = f"Cannot update: missing {source_path}"
            raise ValueError(msg)

        existing_document = Document.model_validate(loads(source_path.read_text(encoding="utf-8")))
        source_url = str(existing_document.metadata.source_url)
        latest_document = await self.extract(source_url)

        existing_ids = {comment.comment_id for comment in existing_document.comments}
        latest_ids = {comment.comment_id for comment in latest_document.comments}
        added_comment_ids = latest_ids - existing_ids

        if mode == "append":
            merged = existing_document.model_copy(deep=True)
            merged.comments.extend(
                [
                    comment
                    for comment in latest_document.comments
                    if comment.comment_id in added_comment_ids
                ]
            )
            merged.metadata = latest_document.metadata
            merged.extraction = latest_document.extraction
            merged.assets = self._merge_assets(existing_document.assets, latest_document.assets)
            document_to_write = merged
        else:
            document_to_write = latest_document

        output_formats = self._detect_formats(archive_path)
        artifacts = await self._build_artifacts(
            document=document_to_write,
            output_formats=output_formats,
            include_comments=True,
        )

        files = [archive_path / name for name in artifacts]
        if dry_run:
            return UpdateResult(
                mode=mode,
                source_url=source_url,
                target_dir=archive_path,
                dry_run=True,
                files=files,
                added_comments=len(added_comment_ids),
            )

        archive_path.mkdir(parents=True, exist_ok=True)
        if mode == "replace":
            self._cleanup_replaced_outputs(archive_path, set(artifacts.keys()))

        for filename, content in artifacts.items():
            target = archive_path / filename
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8")

        return UpdateResult(
            mode=mode,
            source_url=source_url,
            target_dir=archive_path,
            dry_run=False,
            files=files,
            added_comments=len(added_comment_ids),
        )

    async def inspect(self, url: str) -> InspectResult:
        document = await self.extract(url)
        return InspectResult(
            adapter_name=document.extraction.adapter_name,
            fetcher_name=document.extraction.fetcher_name,
            title=document.metadata.title,
            article_blocks=len(document.content),
            comments=len(document.comments),
            images=len(document.assets),
            nested_comment_depth=0,
            authentication_required=self.fetcher_kind == "browser",
        )

    async def extract(self, url: str) -> Document:
        fetch_result = await self.fetcher.fetch(FetchRequest(url=url))
        adapter = self.registry.resolve(fetch_result.final_url)
        document = adapter.parse(fetch_result)
        document.extraction.fetcher_name = self.fetcher.name
        document.extraction.adapter_name = adapter.name
        return document

    def _build_fetcher(self, fetcher_kind: str, profile_dir: Path | None) -> Fetcher:
        if fetcher_kind == "http":
            return HttpFetcher()
        if fetcher_kind == "browser":
            return PlaywrightFetcher(profile_dir=profile_dir, headless=True)
        msg = f"Unsupported fetcher '{fetcher_kind}'"
        raise ValueError(msg)

    async def _build_artifacts(
        self,
        document: Document,
        output_formats: set[str],
        include_comments: bool,
    ) -> dict[str, str | bytes]:
        artifacts: dict[str, str | bytes] = {}
        if "md" in output_formats:
            artifacts["index.md"] = render_markdown(document, include_comments=include_comments)
        if "json" in output_formats:
            artifacts["source.json"] = render_document_json(document) + "\n"
        if "html" in output_formats or "pdf" in output_formats:
            rendered_html = render_html(document, include_comments=include_comments)
            if "html" in output_formats:
                artifacts["print.html"] = rendered_html
            if "pdf" in output_formats:
                artifacts["article.pdf"] = await render_pdf_bytes(rendered_html)
        return artifacts

    def _detect_formats(self, archive_path: Path) -> set[str]:
        formats: set[str] = set()
        if (archive_path / "index.md").exists():
            formats.add("md")
        if (archive_path / "source.json").exists():
            formats.add("json")
        if (archive_path / "print.html").exists():
            formats.add("html")
        if (archive_path / "article.pdf").exists():
            formats.add("pdf")
        return formats or {"md", "json"}

    def _cleanup_replaced_outputs(self, archive_path: Path, keep_files: set[str]) -> None:
        generated_files = {"index.md", "source.json", "print.html", "article.pdf"}
        for filename in generated_files - keep_files:
            target = archive_path / filename
            if target.exists():
                target.unlink()

    def _merge_assets(self, old_assets: list[Asset], new_assets: list[Asset]) -> list[Asset]:
        by_url: dict[str, Asset] = {str(asset.source_url): asset for asset in old_assets}
        for asset in new_assets:
            by_url.setdefault(str(asset.source_url), asset)
        return list(by_url.values())
