set shell := ["bash", "-cu"]

default:
  @just --list

setup:
  uv sync

lint:
  uv run ruff check .

fmt:
  uv run ruff format .

typecheck:
  uv run ty check

test:
  uv run pytest

check:
  just lint
  just typecheck
  just test

run:
  uv run webclip --help

