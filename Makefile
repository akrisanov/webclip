.PHONY: setup lint format typecheck test check run help

setup:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run ty check

test:
	uv run pytest

check: lint typecheck test

run:
	uv run webclip --help

help:
	@echo "Targets:"
	@echo "  setup      Install dependencies with uv"
	@echo "  lint       Run ruff lint checks"
	@echo "  format     Run ruff formatter"
	@echo "  typecheck  Run ty type checks"
	@echo "  test       Run pytest"
	@echo "  check      Run lint + typecheck + test"
	@echo "  run        Run webclip CLI help"

