.PHONY: install test test-live lint fmt typecheck

install:
	uv sync --all-extras

test:
	uv run pytest -m "not live" -q

test-live:
	uv run pytest -m live

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	uv run mypy src
