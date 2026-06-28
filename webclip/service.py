from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from webclip.fetchers.base import Fetcher, FetchRequest
from webclip.fetchers.http import HttpFetcher
from webclip.fetchers.playwright import PlaywrightFetcher
from webclip.models import Document
from webclip.outputs.filesystem import FilesystemOutput, WriteResult
from webclip.registry import AdapterRegistry
from webclip.renderers.html_renderer import render_html
from webclip.renderers.json_renderer import render_document_json
from webclip.renderers.markdown import render_markdown
from webclip.renderers.pdf_renderer import render_pdf_bytes

SUPPORTED_FORMATS = {"md", "json", "html", "pdf"}
SUPPORTED_FETCHERS = {"http", "browser"}


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
    ) -> SaveResult:
        unsupported = output_formats - SUPPORTED_FORMATS
        if unsupported:
            msg = f"Unsupported output format(s): {', '.join(sorted(unsupported))}"
            raise ValueError(msg)

        document = await self.extract(url)
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

        writer = FilesystemOutput(base_dir)
        output = writer.write(
            document=document,
            directory_template=directory_template,
            artifacts=artifacts,
        )
        return SaveResult(document=document, output=output)

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
