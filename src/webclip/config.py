from __future__ import annotations

import os
from pathlib import Path
from tomllib import TOMLDecodeError, load

from pydantic import BaseModel, Field, ValidationError

from webclip.exceptions import ConfigurationError


class AssetConfig(BaseModel):
    download_images: bool = True
    include_avatars: bool = False
    assets_dir: str = "assets"
    max_retries: int = 2
    continue_on_error: bool = True


class RenderingConfig(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["md"])
    markdown_split_files: bool = True
    theme: str = "readable"


class PathsConfig(BaseModel):
    vault: Path | None = None
    directory_template: str = "Clippings/{site}/{slug}"


class CliDefaultsConfig(BaseModel):
    fetcher: str = "http"
    auth_site: str | None = None
    with_comments: bool = True
    update_mode: str = "merge"


class AppConfig(BaseModel):
    paths: PathsConfig = Field(default_factory=PathsConfig)
    assets: AssetConfig = Field(default_factory=AssetConfig)
    rendering: RenderingConfig = Field(default_factory=RenderingConfig)
    cli: CliDefaultsConfig = Field(default_factory=CliDefaultsConfig)


def default_config_path() -> Path:
    return Path.home() / ".config" / "webclip" / "config.toml"


def default_profiles_dir() -> Path:
    return Path.home() / ".config" / "webclip" / "profiles"


def default_declarative_adapters_dir() -> Path:
    return Path.home() / ".config" / "webclip" / "adapters"


def resolve_config_path(override: Path | None = None) -> Path:
    if override is not None:
        return override.expanduser()
    env_path = os.environ.get("WEBCLIP_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return default_config_path()


def load_config(override: Path | None = None) -> AppConfig:
    config_path = resolve_config_path(override)
    if not config_path.exists():
        return AppConfig()
    try:
        with config_path.open("rb") as file:
            raw = load(file)
    except (OSError, TOMLDecodeError) as error:
        msg = f"Failed to read config at {config_path}: {error}"
        raise ConfigurationError(msg) from error
    try:
        return AppConfig.model_validate(raw)
    except ValidationError as error:
        msg = f"Invalid config structure at {config_path}: {error}"
        raise ConfigurationError(msg) from error
