.PHONY: install test test-live test-gemini-live lint fmt typecheck api db-up db-down migrate migrate-new seed-admin-key

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

api:
	uv run uvicorn dnscope.api.main:app --reload --port 8000

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	uv run alembic -c src/dnscope/db/alembic.ini upgrade head

migrate-new:
	uv run alembic -c src/dnscope/db/alembic.ini revision --autogenerate -m "$(m)"

seed-admin-key:
	uv run python -m dnscope.scripts.seed_admin_key
