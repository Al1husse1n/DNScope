import asyncio
import secrets
import uuid
from unittest.mock import patch

from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from dnscope.auth.passwords import compute_hmac, compute_hmac_prefix, hash_api_key
from dnscope.config import Settings
from dnscope.db.repository import ApiKeyRepository
from dnscope.db.session import build_session_factory


# 1. No header -> 401 {"error": "missing_api_key"}
def test_missing_api_key(no_key_client: TestClient) -> None:
    res = no_key_client.get("/investigations")
    assert res.status_code == 401
    assert res.json() == {"error": "missing_api_key"}


# 2. Wrong key -> 401 {"error": "invalid_api_key"}
def test_invalid_api_key(client: TestClient) -> None:
    client.headers["X-API-Key"] = "not-a-valid-api-key"
    res = client.get("/investigations")
    assert res.status_code == 401
    assert res.json() == {"error": "invalid_api_key"}


# 3. Disabled key (is_active=False) -> 401 {"error": "api_key_disabled"}
def test_disabled_api_key(client: TestClient, db_engine: AsyncEngine) -> None:
    raw_key = "disabled-" + secrets.token_urlsafe(32)
    settings = Settings()
    secret = settings.api_key_hmac_secret
    hmac_key = compute_hmac(raw_key, secret)
    hmac_prefix = compute_hmac_prefix(raw_key, secret)
    stored_hash = hash_api_key(hmac_key)

    async def _seed_disabled() -> None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            repo = ApiKeyRepository(session)
            k = await repo.create(
                name="disabled-key",
                key_hash=stored_hash,
                hmac_prefix=hmac_prefix,
                role="user",
            )
            await repo.revoke(k.id)
            await session.commit()

    asyncio.run(_seed_disabled())

    client.headers["X-API-Key"] = raw_key
    res = client.get("/investigations")
    assert res.status_code == 401
    assert res.json() == {"error": "api_key_disabled"}


# 4. Valid user key -> 200 on GET /investigations
def test_valid_user_key(user_client: TestClient) -> None:
    res = user_client.get("/investigations")
    assert res.status_code == 200
    assert "items" in res.json()


# 5. User key hitting /admin/api-keys -> 403 {"error": "admin_required"}
def test_user_key_forbidden_on_admin(user_client: TestClient) -> None:
    res = user_client.get("/admin/api-keys")
    assert res.status_code == 403
    assert res.json() == {"error": "admin_required"}


# 6. Admin key hitting /admin/api-keys -> 200
def test_admin_key_allowed_on_admin(admin_client: TestClient) -> None:
    res = admin_client.get("/admin/api-keys")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# 7. HMAC-prefix path: seed 100 decoy keys + 1 real key; assert require_api_key verifies in <= 2 argon2 calls
def test_hmac_prefix_optimization(client: TestClient, db_engine: AsyncEngine) -> None:
    settings = Settings()
    secret = settings.api_key_hmac_secret
    real_raw_key = "target-key-" + secrets.token_urlsafe(32)
    real_hmac = compute_hmac(real_raw_key, secret)
    real_prefix = compute_hmac_prefix(real_raw_key, secret)
    real_hash = hash_api_key(real_hmac)

    async def _seed_100_decoys() -> None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            repo = ApiKeyRepository(session)
            # Insert real key
            await repo.create(
                name="real-key",
                key_hash=real_hash,
                hmac_prefix=real_prefix,
                role="user",
            )
            # Insert 100 decoy keys with distinct random prefixes
            for i in range(100):
                decoy_raw = f"decoy-{i}-" + secrets.token_urlsafe(32)
                decoy_prefix = compute_hmac_prefix(decoy_raw, secret)
                await repo.create(
                    name=f"decoy-{i}",
                    key_hash=f"decoy-hash-{i}",
                    hmac_prefix=decoy_prefix,
                    role="user",
                )
            await session.commit()

    asyncio.run(_seed_100_decoys())

    client.headers["X-API-Key"] = real_raw_key
    with patch.object(PasswordHasher, "verify", wraps=PasswordHasher().verify) as spy_verify:
        res = client.get("/investigations")
        assert res.status_code == 200
        # Verification must be O(1) via prefix lookup, calling argon2 verify <= 2 times
        assert spy_verify.call_count <= 2
        assert spy_verify.call_count >= 1


# 8. last_used_at updated after a request
def test_last_used_at_updated(
    user_client: TestClient,
    seed_user_key: tuple[str, uuid.UUID],
    db_engine: AsyncEngine,
) -> None:
    _, key_id = seed_user_key

    # Check last_used_at is initially None
    async def _get_last_used() -> str | None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            repo = ApiKeyRepository(session)
            k = await repo.get_by_id(key_id)
            return str(k.last_used_at) if k and k.last_used_at else None

    assert asyncio.run(_get_last_used()) is None

    # Make request
    res = user_client.get("/investigations")
    assert res.status_code == 200

    # Verify last_used_at is now set
    updated = asyncio.run(_get_last_used())
    assert updated is not None


# 9. X-Request-ID header present on 401 responses too
def test_request_id_present_on_401(no_key_client: TestClient) -> None:
    res = no_key_client.get("/investigations")
    assert res.status_code == 401
    assert "X-Request-ID" in res.headers


# 10. Health endpoint requires no auth
def test_health_requires_no_auth(no_key_client: TestClient) -> None:
    res = no_key_client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": "ok"}


# 11. generate_api_key format
def test_generate_api_key_format() -> None:
    from dnscope.auth.passwords import generate_api_key

    key = generate_api_key()
    assert isinstance(key, str)
    assert len(key) >= 32


# 12. compute_hmac deterministic
def test_compute_hmac_deterministic() -> None:
    h1 = compute_hmac("secret-key", "salt")
    h2 = compute_hmac("secret-key", "salt")
    assert h1 == h2
    assert compute_hmac("secret-key", "other-salt") != h1


# 13. compute_hmac_prefix length and prefix match
def test_compute_hmac_prefix_length() -> None:
    prefix = compute_hmac_prefix("secret-key", "salt")
    assert len(prefix) == 16
    assert compute_hmac("secret-key", "salt").startswith(prefix)


# 14. hash_api_key and verify_api_key success
def test_hash_and_verify_api_key() -> None:
    from dnscope.auth.passwords import generate_api_key, hash_api_key, verify_api_key

    key = generate_api_key()
    hmac_val = compute_hmac(key, "test-secret")
    hashed = hash_api_key(hmac_val)
    assert verify_api_key(hmac_val, hashed) is True


# 15. verify_api_key wrong secret returns False
def test_verify_api_key_wrong_secret() -> None:
    from dnscope.auth.passwords import generate_api_key, hash_api_key, verify_api_key

    key = generate_api_key()
    hmac_val = compute_hmac(key, "test-secret")
    wrong_hmac = compute_hmac(key, "wrong-secret")
    hashed = hash_api_key(hmac_val)
    assert verify_api_key(wrong_hmac, hashed) is False


# 16. verify_api_key wrong key returns False
def test_verify_api_key_wrong_key() -> None:
    from dnscope.auth.passwords import generate_api_key, hash_api_key, verify_api_key

    key = generate_api_key()
    hmac_val = compute_hmac(key, "test-secret")
    wrong_hmac = compute_hmac("wrong_key", "test-secret")
    hashed = hash_api_key(hmac_val)
    assert verify_api_key(wrong_hmac, hashed) is False


# 17. verify_api_key corrupted hash returns False
def test_verify_api_key_corrupted_hash() -> None:
    from dnscope.auth.passwords import generate_api_key, verify_api_key

    key = generate_api_key()
    hmac_val = compute_hmac(key, "test-secret")
    assert verify_api_key(hmac_val, "not-a-valid-argon2-hash") is False


# 18. ApiKeyContext dataclass
def test_api_key_context_dataclass() -> None:
    from dnscope.auth.models import ApiKeyContext, Role

    ctx = ApiKeyContext(key_id=uuid.uuid4(), role=Role.ADMIN, name="test-name")
    assert ctx.role == "admin"
    assert ctx.name == "test-name"
