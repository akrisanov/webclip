from pathlib import Path

from webclip.registry import AdapterRegistry


def test_registry_loads_declarative_adapter(tmp_path: Path) -> None:
    spec = tmp_path / "example.toml"
    spec.write_text(
        "\n".join(
            [
                'name = "example-declarative"',
                'hosts = ["example.org"]',
                "",
                "[selectors]",
                'title = "h1"',
                'content_root = "article"',
            ]
        ),
        encoding="utf-8",
    )
    registry = AdapterRegistry(declarative_dir=tmp_path)
    names = [adapter.name for adapter in registry.list_adapters()]
    assert "example-declarative" in names

    resolved = registry.resolve("https://example.org/post/1")
    assert resolved.name == "example-declarative"
