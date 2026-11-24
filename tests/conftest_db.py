import asyncio
import logging
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import NullPool
from starlette.testclient import TestClient

from dnscope.api.main import app
from dnscope.config import Settings
from dnscope.db.base import Base
from dnscope.db.session import build_engine, build_session_factory


@pytest.fixture(scope="session")
def db_engine() -> Iterator[AsyncEngine]:
    settings = Settings()
    engine = build_engine(settings.database_url, poolclass=NullPool)

    async def _check_and_init() -> None:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1;"))
                await conn.run_sync(Base.metadata.create_all)
                await conn.commit()
        except Exception as exc:
            pytest.fail(
                f"P4 tests require PostgreSQL. Run 'make db-up' first. "
                f"Set DATABASE_URL or use the default localhost:5432/dnscope. Error: {exc}"
            )

    asyncio.run(_check_and_init())

    yield engine

    async def _teardown() -> None:
        try:
            async with engine.connect() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
                await conn.commit()
        except Exception as exc:
            logging.getLogger().debug("Teardown drop_all exception: %s", exc)
        await engine.dispose()

    asyncio.run(_teardown())


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Provide a transactional session that rolls back after each test."""
    async with db_engine.connect() as connection:
        trans = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
def client(db_engine: AsyncEngine) -> Iterator[TestClient]:
    """Build TestClient with isolated DB state per test."""

    # Ensure tables are clean before running the test
    async def _clean() -> None:
        async with db_engine.connect() as conn:
            await conn.execute(
                text(
                    "TRUNCATE TABLE investigations, investigation_jobs, api_keys, public_investigations CASCADE;"
                )
            )
            await conn.commit()

    asyncio.run(_clean())

    app.state.session_factory = build_session_factory(db_engine)

    with TestClient(app) as test_client:
        yield test_client

    asyncio.run(_clean())
