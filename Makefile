.PHONY: install test test-live test-gemini-live lint fmt typecheck

install:
	uv sync --all-extras

test:
	uv run pytest -m "not live and not gemini_live" -q

test-live:
	uv run pytest -m live

test-gemini-live:
	uv run pytest -m gemini_live

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	uv run mypy src
