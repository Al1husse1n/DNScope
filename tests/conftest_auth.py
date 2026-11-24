import asyncio
import secrets
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from dnscope.auth.passwords import compute_hmac, compute_hmac_prefix, hash_api_key
from dnscope.config import Settings
from dnscope.db.repository import ApiKeyRepository
from dnscope.db.session import build_session_factory


@pytest.fixture
def seed_user_key(db_engine: AsyncEngine) -> tuple[str, uuid.UUID]:
    raw_key = "user-" + secrets.token_urlsafe(32)
    settings = Settings()
    secret = settings.api_key_hmac_secret
    hmac_key = compute_hmac(raw_key, secret)
    hmac_prefix = compute_hmac_prefix(raw_key, secret)
    stored_hash = hash_api_key(hmac_key)
    key_id: uuid.UUID = uuid.uuid4()

    async def _seed() -> None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            repo = ApiKeyRepository(session)
            key = await repo.create(
                name="test-user",
                key_hash=stored_hash,
                hmac_prefix=hmac_prefix,
                role="user",
            )
            nonlocal key_id
            key_id = key.id
            await session.commit()

    asyncio.run(_seed())
    return raw_key, key_id


@pytest.fixture
def seed_admin_key(db_engine: AsyncEngine) -> tuple[str, uuid.UUID]:
    raw_key = "admin-" + secrets.token_urlsafe(32)
    settings = Settings()
    secret = settings.api_key_hmac_secret
    hmac_key = compute_hmac(raw_key, secret)
    hmac_prefix = compute_hmac_prefix(raw_key, secret)
    stored_hash = hash_api_key(hmac_key)
    key_id: uuid.UUID = uuid.uuid4()

    async def _seed() -> None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            repo = ApiKeyRepository(session)
            key = await repo.create(
                name="test-admin",
                key_hash=stored_hash,
                hmac_prefix=hmac_prefix,
                role="admin",
            )
            nonlocal key_id
            key_id = key.id
            await session.commit()

    asyncio.run(_seed())
    return raw_key, key_id


@pytest.fixture
def user_client(client: TestClient, seed_user_key: tuple[str, uuid.UUID]) -> TestClient:
    raw_key, _ = seed_user_key
    client.headers["X-API-Key"] = raw_key
    return client


@pytest.fixture
def admin_client(client: TestClient, seed_admin_key: tuple[str, uuid.UUID]) -> TestClient:
    raw_key, _ = seed_admin_key
    client.headers["X-API-Key"] = raw_key
    return client


@pytest.fixture
def no_key_client(client: TestClient) -> TestClient:
    client.headers.pop("X-API-Key", None)
    return client
