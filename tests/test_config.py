from pathlib import Path

from webclip.config import load_config


def test_load_config_uses_defaults_when_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.toml")
    assert config.rendering.formats == ["md"]
    assert config.cli.fetcher == "http"
    assert config.assets.max_retries == 2


def test_load_config_parses_custom_values(tmp_path: Path) -> None:
    config_path = tmp_path / "webclip.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'directory_template = "WebClips/{site}/{slug}"',
                "",
                "[rendering]",
                'formats = ["md", "html"]',
                'theme = "serif"',
                "",
                "[cli]",
                'fetcher = "browser"',
                "with_comments = false",
                "",
                "[assets]",
                "max_retries = 5",
                "continue_on_error = false",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)
    assert config.paths.directory_template == "WebClips/{site}/{slug}"
    assert config.rendering.formats == ["md", "html"]
    assert config.rendering.theme == "serif"
    assert config.cli.fetcher == "browser"
    assert config.cli.with_comments is False
    assert config.assets.max_retries == 5
    assert config.assets.continue_on_error is False
