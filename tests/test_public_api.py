import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from dnscope.api.daily_counter import DailyCounter
from dnscope.api.main import app
from dnscope.auth.rate_limit import InMemoryRateLimiter
from dnscope.db.models import PublicInvestigation
from dnscope.db.public_repository import PublicResultRepository
from dnscope.schemas.common import RiskLevel
from dnscope.schemas.scoring import RuleHit, ScoreResult
from dnscope.schemas.supervisor import SupervisorAssessment


class FakeGraph:
    def __init__(
        self,
        canned_assessment: SupervisorAssessment | None = None,
    ) -> None:
        self.call_count = 0
        score_res = ScoreResult(
            score=10,
            risk_level=RiskLevel.LOW,
            rule_hits=[
                RuleHit(
                    rule_id="TEST_RULE",
                    description="Test",
                    points=10,
                    evidence_refs=[],
                )
            ],
            total_points_before_clamp=10,
        )
        self.assessment = canned_assessment or SupervisorAssessment(
            score_result=score_res,
            rule_trace_explanation="trace",
            narrative="Analyst narrative from Gemini",
            inconclusive_checks=[],
        )

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        return {"assessment": self.assessment, "domain": state["domain"]}


@pytest.fixture(autouse=True)
def reset_public_state(request: pytest.FixtureRequest) -> None:
    """Reset public limiter and daily counter after TestClient lifespan."""
    for name in ("no_key_client", "client", "admin_client"):
        if name in request.fixturenames:
            request.getfixturevalue(name)
            break
    app.state.public_limiter = InMemoryRateLimiter(limit_per_minute=10, window_seconds=3600.0)
    app.state.daily_llm_counter = DailyCounter(cap=500)
    app.state.graph = FakeGraph()
    app.state.null_graph = FakeGraph(
        canned_assessment=SupervisorAssessment(
            score_result=ScoreResult(
                score=10,
                risk_level=RiskLevel.LOW,
                rule_hits=[],
                total_points_before_clamp=10,
            ),
            rule_trace_explanation="trace",
            narrative=None,
            inconclusive_checks=[],
        )
    )


def test_public_investigate_success_no_key(no_key_client: TestClient) -> None:
    """1. POST /investigate with example.com and no X-API-Key header -> 201."""
    res = no_key_client.post("/investigate", json={"domain": "example.com"})
    assert res.status_code == 201
    data = res.json()
    assert "share_id" in data
    assert uuid.UUID(data["share_id"])
    assert data["domain"] == "example.com"
    assert data["normalized_domain"] == "example.com"
    assert data["narrative_source"] == "gemini"
    assert "assessment" in data
    assert data["assessment"]["score_result"]["score"] == 10


def test_public_investigate_invalid_domain_zero_graph_calls(no_key_client: TestClient) -> None:
    """2. POST /investigate with invalid domain -> 400 with zero graph calls."""
    fake_graph: FakeGraph = app.state.graph
    res = no_key_client.post("/investigate", json={"domain": "http://invalid-with-scheme.com"})
    assert res.status_code == 400
    assert res.json()["error"] == "invalid_domain"
    assert fake_graph.call_count == 0


def test_public_investigate_rate_limit_11th_request(no_key_client: TestClient) -> None:
    """3. POST /investigate 11 times from same IP in 1 hour -> 10th is 201, 11th is 429."""
    headers = {"X-Forwarded-For": "203.0.113.195"}
    for i in range(10):
        res = no_key_client.post(
            "/investigate",
            json={"domain": f"domain-{i}.com"},
            headers=headers,
        )
        assert res.status_code == 201, f"Expected 201 on request {i + 1}"

    # 11th request must be rate limited
    res11 = no_key_client.post(
        "/investigate",
        json={"domain": "domain-11.com"},
        headers=headers,
    )
    assert res11.status_code == 429
    assert "Retry-After" in res11.headers
    assert int(res11.headers["Retry-After"]) >= 1


def test_public_investigate_independent_ips(no_key_client: TestClient) -> None:
    """4. POST /investigate from two different IPs -> both succeed."""
    res1 = no_key_client.post(
        "/investigate",
        json={"domain": "test-ip1.com"},
        headers={"X-Forwarded-For": "198.51.100.1"},
    )
    res2 = no_key_client.post(
        "/investigate",
        json={"domain": "test-ip2.com"},
        headers={"X-Forwarded-For": "198.51.100.2"},
    )
    assert res1.status_code == 201
    assert res2.status_code == 201


def test_public_rate_limit_ignores_api_key_header(client: TestClient) -> None:
    """5. Rate limit is IP-based: X-API-Key header is ignored, rate limit still applies by IP."""
    headers = {
        "X-Forwarded-For": "192.0.2.55",
        "X-API-Key": "some-random-or-valid-key",
    }
    for _ in range(10):
        res = client.post("/investigate", json={"domain": "keyed-rate-limit.org"}, headers=headers)
        assert res.status_code == 201

    res_exceeded = client.post(
        "/investigate",
        json={"domain": "keyed-rate-limit.org"},
        headers=headers,
    )
    assert res_exceeded.status_code == 429


def test_get_public_result_roundtrip(no_key_client: TestClient) -> None:
    """6. GET /r/{share_id} with fresh share_id -> 200 with same body."""
    post_res = no_key_client.post("/investigate", json={"domain": "roundtrip.com"})
    assert post_res.status_code == 201
    post_data = post_res.json()
    share_id = post_data["share_id"]

    get_res = no_key_client.get(f"/r/{share_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["share_id"] == share_id
    assert get_data["domain"] == "roundtrip.com"
    assert get_data["assessment"]["score_result"]["score"] == 10


def test_get_public_result_not_found(no_key_client: TestClient) -> None:
    """7. GET /r/{share_id} with random UUID -> 404."""
    random_id = uuid.uuid4()
    res = no_key_client.get(f"/r/{random_id}")
    assert res.status_code == 404


def test_ttl_expiry_lazy_deletion(no_key_client: TestClient) -> None:
    """8. TTL expiry: insert row with expires_at in the past -> 404 and deleted on read."""
    session_factory = app.state.session_factory
    share_id = uuid.uuid4()
    past_time = datetime.now(UTC) - timedelta(hours=2)

    async def _insert_expired() -> None:
        async with session_factory() as session:
            inv = PublicInvestigation(
                share_id=share_id,
                domain="expired.com",
                normalized_domain="expired.com",
                result={
                    "share_id": str(share_id),
                    "domain": "expired.com",
                    "normalized_domain": "expired.com",
                    "created_at": past_time.isoformat(),
                    "assessment": {},
                    "narrative_source": "gemini",
                },
                expires_at=past_time,
            )
            session.add(inv)
            await session.commit()

    assert no_key_client.portal is not None
    no_key_client.portal.call(_insert_expired)

    # GET request should return 404 and lazily delete
    res = no_key_client.get(f"/r/{share_id}")
    assert res.status_code == 404

    # Verify row was actually deleted in repository.get
    async def _verify_deleted() -> None:
        async with session_factory() as session:
            repo = PublicResultRepository(session)
            item = await repo.get(share_id)
            assert item is None

    no_key_client.portal.call(_verify_deleted)


def test_daily_llm_cap_fallback(no_key_client: TestClient) -> None:
    """9. Daily LLM cap: set cap=2; 3rd request -> narrative_source: deterministic_only and NullExplainer narrative."""
    app.state.daily_llm_counter = DailyCounter(cap=2)

    # 1st request -> gemini
    r1 = no_key_client.post("/investigate", json={"domain": "cap-test-1.com"})
    assert r1.status_code == 201
    assert r1.json()["narrative_source"] == "gemini"

    # 2nd request -> gemini
    r2 = no_key_client.post("/investigate", json={"domain": "cap-test-2.com"})
    assert r2.status_code == 201
    assert r2.json()["narrative_source"] == "gemini"

    # 3rd request -> cap exceeded, fallback to deterministic_only
    r3 = no_key_client.post("/investigate", json={"domain": "cap-test-3.com"})
    assert r3.status_code == 201
    data3 = r3.json()
    assert data3["narrative_source"] == "deterministic_only"
    assert data3["assessment"]["narrative"] == "Narrative generation not enabled."


def test_daily_cap_resets_at_utc_midnight(monkeypatch: pytest.MonkeyPatch) -> None:
    """10. Daily cap resets at UTC midnight."""
    counter = DailyCounter(cap=1)
    assert counter.try_increment() is True
    assert counter.try_increment() is False

    # Advance time to tomorrow
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    fake_datetime = MagicMock(wraps=datetime)
    fake_datetime.now.return_value = tomorrow
    monkeypatch.setattr("dnscope.api.daily_counter.datetime", fake_datetime)

    # Counter should allow again
    assert counter.try_increment() is True


def test_get_shared_result_counts_against_rate_limit(no_key_client: TestClient) -> None:
    """11. GET /r/{id} counts against the same IP rate limit."""
    headers = {"X-Forwarded-For": "198.51.100.99"}

    # Create 1 shared result
    create_res = no_key_client.post(
        "/investigate",
        json={"domain": "shared-ratelimit.com"},
        headers=headers,
    )
    assert create_res.status_code == 201
    share_id = create_res.json()["share_id"]

    # 9 reads from the same IP (10th total request from this IP)
    for _ in range(9):
        r = no_key_client.get(f"/r/{share_id}", headers=headers)
        assert r.status_code == 200

    # 11th request from this IP must be 429
    r11 = no_key_client.get(f"/r/{share_id}", headers=headers)
    assert r11.status_code == 429


def test_api_key_endpoints_still_work_regression(admin_client: TestClient) -> None:
    """12. Existing API-key endpoints still work (POST /investigations with valid key returns 202)."""
    res = admin_client.post("/investigations", json={"domain": "key-regression.com"})
    assert res.status_code == 202
    assert "job_id" in res.json()


def test_public_investigate_normalized_domain_is_string(
    no_key_client: TestClient,
) -> None:
    """Regression test for P7 bug: normalized_domain must be a str,
    not a ValidatedDomain dataclass, in both the response and the DB row."""
    res = no_key_client.post("/investigate", json={"domain": "Example.COM."})
    assert res.status_code == 201
    body = res.json()
    assert isinstance(body["normalized_domain"], str)
    assert body["normalized_domain"] == "example.com"
    # Verify the DB row also stores it as a string
    share_id = body["share_id"]
    followup = no_key_client.get(f"/r/{share_id}")
    assert followup.status_code == 200
    assert isinstance(followup.json()["normalized_domain"], str)
