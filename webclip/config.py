from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AssetConfig(BaseModel):
    download_images: bool = True
    include_avatars: bool = False
    assets_dir: str = "assets"


class RenderingConfig(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["md"])
    markdown_split_files: bool = True
    pdf_theme: str = "readable"


class PathsConfig(BaseModel):
    vault: Path | None = None
    directory_template: str = "Clippings/{site}/{slug}"


class AppConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    assets: AssetConfig = Field(default_factory=AssetConfig)
    rendering: RenderingConfig = Field(default_factory=RenderingConfig)


def default_config_path() -> Path:
    return Path.home() / ".config" / "webclip" / "config.toml"

