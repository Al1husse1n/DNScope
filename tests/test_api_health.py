from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from starlette.testclient import TestClient

from dnscope.api.main import app


# 1. /health returns 200 when DB reachable
def test_health_success(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "db": "ok"}
    assert "X-Request-ID" in response.headers


# 2. /health returns 503 when DB connectivity fails
def test_health_db_failure(client: TestClient) -> None:
    @asynccontextmanager
    async def _failing_factory() -> AsyncIterator[Any]:
        raise ConnectionError("DB connection refused")
        yield  # type: ignore[unreachable]

    original_factory = app.state.session_factory
    app.state.session_factory = _failing_factory
    try:
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data == {"status": "degraded", "db": "unreachable"}
        assert "X-Request-ID" in response.headers
    finally:
        app.state.session_factory = original_factory
