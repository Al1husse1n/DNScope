.PHONY: install test lint fmt typecheck

install:
	uv sync --all-extras

test:
	uv run pytest -q

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	uv run mypy src

