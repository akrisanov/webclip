from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

from webclip.models import Asset, Document

_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


@dataclass(frozen=True)
class AssetDownloadResult:
    document: Document
    artifacts: dict[str, bytes]
    url_map: dict[str, str]


async def localize_document_assets(
    document: Document,
    fetch_asset: AssetFetcher,
    assets_dir_name: str = "assets",
) -> AssetDownloadResult:
    artifacts: dict[str, bytes] = {}
    url_map: dict[str, str] = {}
    updated_assets: list[Asset] = []

    seen_urls: set[str] = set()
    index = 1
    for asset in document.assets:
        source_url = str(asset.source_url)
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)
        content, mime = await fetch_asset(source_url)
        extension = _pick_extension(source_url, mime)
        filename = f"asset-{index:03d}{extension}"
        index += 1
        relative_path = str(Path(assets_dir_name) / filename)
        url_map[source_url] = relative_path
        artifacts[relative_path] = content
        updated_assets.append(
            asset.model_copy(
                update={
                    "local_path": relative_path,
                    "mime": mime,
                    "sha256": sha256(content).hexdigest(),
                }
            )
        )

    updated_document = document.model_copy(update={"assets": updated_assets}, deep=True)
    return AssetDownloadResult(document=updated_document, artifacts=artifacts, url_map=url_map)


class AssetFetcher(Protocol):
    async def __call__(self, url: str) -> tuple[bytes, str | None]: ...


def _pick_extension(source_url: str, mime: str | None) -> str:
    path_suffix = Path(urlparse(source_url).path).suffix.lower()
    if path_suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return ".jpg" if path_suffix == ".jpeg" else path_suffix
    if mime is not None and mime in _MIME_TO_EXT:
        return _MIME_TO_EXT[mime]
    return ".bin"
