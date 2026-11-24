import time
import uuid

from starlette.testclient import TestClient

from dnscope.api.main import app
from dnscope.auth.rate_limit import InMemoryRateLimiter


# 1. Under-limit requests pass (unit)
def test_limiter_unit_under_limit() -> None:
    limiter = InMemoryRateLimiter(limit_per_minute=5, window_seconds=60.0)
    key_id = uuid.uuid4()
    for _ in range(5):
        allowed, retry_after = limiter.check(key_id)
        assert allowed is True
        assert retry_after == 0.0


# 2. Limit + 1 -> 429, Retry-After header present, integer seconds >= 1 (unit & endpoint)
def test_limiter_unit_over_limit() -> None:
    limiter = InMemoryRateLimiter(limit_per_minute=2, window_seconds=60.0)
    key_id = uuid.uuid4()
    assert limiter.check(key_id).allowed is True
    assert limiter.check(key_id).allowed is True

    # 3rd request exceeds limit
    result = limiter.check(key_id)
    assert result.allowed is False
    assert result.retry_after >= 1.0


# 3. Two different keys have independent limiters
def test_limiter_keys_independent() -> None:
    limiter = InMemoryRateLimiter(limit_per_minute=1, window_seconds=60.0)
    key_a = uuid.uuid4()
    key_b = uuid.uuid4()

    assert limiter.check(key_a).allowed is True
    assert limiter.check(key_a).allowed is False

    # Key B is unaffected by Key A's limit
    assert limiter.check(key_b).allowed is True
    assert limiter.check(key_b).allowed is False


# 4. Sliding window: after window_seconds elapses, requests allowed again
def test_limiter_sliding_window_expiry() -> None:
    limiter = InMemoryRateLimiter(limit_per_minute=1, window_seconds=0.1)
    key_id = uuid.uuid4()

    assert limiter.check(key_id).allowed is True
    assert limiter.check(key_id).allowed is False

    # Wait for the 0.1s sliding window to expire
    time.sleep(0.12)
    assert limiter.check(key_id).allowed is True


# 5. Endpoint integration: 429 on limit exceeded with Retry-After header and body
def test_rate_limit_endpoint_integration(user_client: TestClient) -> None:
    # Set limit to 2 per minute for testing
    original_limiter = app.state.rate_limiter
    app.state.rate_limiter = InMemoryRateLimiter(limit_per_minute=2, window_seconds=60.0)
    try:
        # First 2 requests pass (e.g. POST /investigations with invalid domain to return 400 quickly)
        r1 = user_client.post("/investigations", json={"domain": "invalid..domain"})
        assert r1.status_code == 400

        r2 = user_client.post("/investigations", json={"domain": "invalid..domain"})
        assert r2.status_code == 400

        # 3rd request exceeds rate limit
        r3 = user_client.post("/investigations", json={"domain": "invalid..domain"})
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
        retry_after_hdr = int(r3.headers["Retry-After"])
        assert retry_after_hdr >= 1

        body = r3.json()
        assert body.get("error") == "rate_limited"
        assert body.get("retry_after") == retry_after_hdr
    finally:
        app.state.rate_limiter = original_limiter
