from typer.testing import CliRunner

from webclip.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "web clipping CLI" in result.stdout


def test_adapters_list() -> None:
    result = runner.invoke(app, ["adapters", "list"])
    assert result.exit_code == 0
    assert "vas3k" in result.stdout
    assert "generic" in result.stdout

