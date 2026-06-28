from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass, field
from json import loads
from mimetypes import guess_type
from pathlib import Path

import httpx

from webclip.assets.downloader import localize_document_assets
from webclip.exceptions import AssetFetchError
from webclip.fetchers.base import Fetcher, FetchRequest
from webclip.fetchers.http import HttpFetcher
from webclip.fetchers.playwright import PlaywrightFetcher
from webclip.models import Asset, Document
from webclip.outputs.filesystem import FilesystemOutput, WriteResult
from webclip.outputs.obsidian import ObsidianOutput
from webclip.registry import AdapterRegistry
from webclip.renderers.html_renderer import SUPPORTED_THEMES, render_html
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
    downloaded_assets: int = 0
    failed_assets: list[str] = field(default_factory=list)


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
    downloaded_assets: int = 0
    failed_assets: list[str] = field(default_factory=list)


class WebclipService:
    def __init__(
        self,
        registry: AdapterRegistry | None = None,
        fetcher_kind: str = "http",
        profile_dir: Path | None = None,
        assets_dir_name: str = "assets",
        asset_max_retries: int = 2,
        asset_continue_on_error: bool = True,
    ) -> None:
        self.registry = registry or AdapterRegistry()
        self.fetcher = self._build_fetcher(fetcher_kind=fetcher_kind, profile_dir=profile_dir)
        self.fetcher_kind = fetcher_kind
        self.assets_dir_name = assets_dir_name
        self.asset_max_retries = max(asset_max_retries, 0)
        self.asset_continue_on_error = asset_continue_on_error

    async def save(
        self,
        url: str,
        output_formats: set[str],
        base_dir: Path,
        directory_template: str,
        include_comments: bool,
        use_obsidian_output: bool = False,
        theme: str = "readable",
    ) -> SaveResult:
        self._validate_render_options(output_formats=output_formats, theme=theme)

        document = await self.extract(url)
        writer = ObsidianOutput(base_dir) if use_obsidian_output else FilesystemOutput(base_dir)
        output_dir = writer.resolve_output_dir(
            document=document,
            directory_template=directory_template,
        )
        localized = await localize_document_assets(
            document,
            fetch_asset=self._fetch_asset,
            assets_dir_name=self.assets_dir_name,
            continue_on_error=self.asset_continue_on_error,
        )
        artifacts = await self.render_document(
            document=localized.document,
            output_formats=output_formats,
            include_comments=include_comments,
            theme=theme,
            asset_url_map=localized.url_map,
            base_href=f"{output_dir.resolve().as_uri()}/",
            pdf_resolve_dir=output_dir,
            asset_artifacts=localized.artifacts,
        )
        artifacts = {**localized.artifacts, **artifacts}

        output = writer.write_to_directory(
            output_dir=output_dir,
            artifacts=artifacts,
        )
        return SaveResult(
            document=localized.document,
            output=output,
            downloaded_assets=len(localized.artifacts),
            failed_assets=localized.failed_urls,
        )

    async def render_document(
        self,
        document: Document,
        output_formats: set[str],
        include_comments: bool = True,
        theme: str = "readable",
        asset_url_map: dict[str, str] | None = None,
        base_href: str | None = None,
        pdf_resolve_dir: Path | None = None,
        asset_artifacts: dict[str, bytes] | None = None,
    ) -> dict[str, str | bytes]:
        self._validate_render_options(output_formats=output_formats, theme=theme)
        return await self._build_artifacts(
            document=document,
            output_formats=output_formats,
            include_comments=include_comments,
            theme=theme,
            asset_url_map=asset_url_map or self._asset_map_from_document(document),
            base_href=base_href,
            pdf_resolve_dir=pdf_resolve_dir,
            asset_artifacts=asset_artifacts or {},
        )

    async def update(
        self,
        archive_path: Path,
        mode: str,
        dry_run: bool = False,
        theme: str = "readable",
    ) -> UpdateResult:
        if mode not in SUPPORTED_UPDATE_MODES:
            msg = f"Unsupported update mode '{mode}'"
            raise ValueError(msg)
        self._validate_render_options(output_formats=SUPPORTED_FORMATS, theme=theme)

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
        localized_artifacts: dict[str, bytes] = {}
        asset_url_map = self._asset_map_from_document(document_to_write)
        if not dry_run:
            localized = await localize_document_assets(
                document_to_write,
                fetch_asset=self._fetch_asset,
                assets_dir_name=self.assets_dir_name,
                continue_on_error=self.asset_continue_on_error,
            )
            document_to_write = localized.document
            localized_artifacts = localized.artifacts
            asset_url_map = localized.url_map
            failed_assets = localized.failed_urls
        else:
            failed_assets = []

        artifacts = await self.render_document(
            document=document_to_write,
            output_formats=output_formats,
            include_comments=True,
            theme=theme,
            asset_url_map=asset_url_map,
            base_href=f"{archive_path.resolve().as_uri()}/",
            pdf_resolve_dir=None if dry_run else archive_path,
            asset_artifacts=localized_artifacts,
        )
        artifacts = {**localized_artifacts, **artifacts}

        files = [archive_path / name for name in artifacts]
        if dry_run:
            return UpdateResult(
                mode=mode,
                source_url=source_url,
                target_dir=archive_path,
                dry_run=True,
                files=files,
                added_comments=len(added_comment_ids),
                downloaded_assets=0,
                failed_assets=[],
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
            downloaded_assets=len(localized_artifacts),
            failed_assets=failed_assets,
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
        theme: str,
        asset_url_map: dict[str, str],
        base_href: str | None,
        pdf_resolve_dir: Path | None,
        asset_artifacts: dict[str, bytes],
    ) -> dict[str, str | bytes]:
        artifacts: dict[str, str | bytes] = {}
        if "md" in output_formats:
            artifacts["index.md"] = render_markdown(
                document,
                include_comments=include_comments,
                asset_url_map=asset_url_map,
            )
        if "json" in output_formats:
            artifacts["source.json"] = render_document_json(document) + "\n"
        if "html" in output_formats:
            artifacts["print.html"] = render_html(
                document,
                include_comments=include_comments,
                theme=theme,
                asset_url_map=asset_url_map,
                base_href=None,
            )
        if "pdf" in output_formats:
            pdf_asset_map = self._build_pdf_asset_map(
                asset_url_map=asset_url_map,
                pdf_resolve_dir=pdf_resolve_dir,
                asset_artifacts=asset_artifacts,
            )
            rendered_pdf_html = render_html(
                document,
                include_comments=include_comments,
                theme=theme,
                asset_url_map=pdf_asset_map,
                base_href=base_href,
            )
            artifacts["article.pdf"] = await render_pdf_bytes(
                rendered_pdf_html,
                resolve_dir=pdf_resolve_dir,
            )
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

    def _validate_render_options(self, output_formats: set[str], theme: str) -> None:
        unsupported = output_formats - SUPPORTED_FORMATS
        if unsupported:
            msg = f"Unsupported output format(s): {', '.join(sorted(unsupported))}"
            raise ValueError(msg)
        if theme not in SUPPORTED_THEMES:
            msg = f"Unsupported theme '{theme}'"
            raise ValueError(msg)

    async def _fetch_asset(self, url: str) -> tuple[bytes, str | None]:
        headers = {"User-Agent": "webclip/0.1 (+https://local.cli)"}
        attempts = self.asset_max_retries + 1
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers=headers,
        ) as client:
            for attempt in range(attempts):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError as error:
                    if attempt + 1 >= attempts:
                        msg = f"Asset download failed for {url}: {error}"
                        raise AssetFetchError(msg) from error
                    continue
                mime = response.headers.get("content-type")
                if mime is not None:
                    mime = mime.split(";", 1)[0].strip().lower()
                return response.content, mime
        msg = f"Asset download failed for {url}"
        raise AssetFetchError(msg)

    def _asset_map_from_document(self, document: Document) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for asset in document.assets:
            if asset.local_path is not None:
                mapping[str(asset.source_url)] = asset.local_path
        return mapping

    def _build_pdf_asset_map(
        self,
        asset_url_map: dict[str, str],
        pdf_resolve_dir: Path | None,
        asset_artifacts: dict[str, bytes],
    ) -> dict[str, str]:
        if pdf_resolve_dir is None:
            return asset_url_map
        mapping = dict(asset_url_map)
        for source_url, target in asset_url_map.items():
            if target.startswith(("http://", "https://", "data:", "file://")):
                continue
            mime_type = guess_type(Path(target).name)[0] or "application/octet-stream"
            asset_bytes = asset_artifacts.get(target)
            if asset_bytes is None:
                asset_path = pdf_resolve_dir / target
                if not asset_path.exists() or not asset_path.is_file():
                    continue
                asset_bytes = asset_path.read_bytes()
            encoded = b64encode(asset_bytes).decode("ascii")
            mapping[source_url] = f"data:{mime_type};base64,{encoded}"
        return mapping
