from starlette.testclient import TestClient

from dnscope.api.main import app


def test_cors_preflight_allowed_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/investigations",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-api-key" in allowed_headers


def test_cors_disallowed_origin() -> None:
    client = TestClient(app)
    response = client.options(
        "/investigations",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Disallowed origin should not receive Access-Control-Allow-Origin header
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_for_api_key_header() -> None:
    client = TestClient(app)
    response = client.options(
        "/investigations",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key, Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-api-key" in allowed_headers
    assert "content-type" in allowed_headers

