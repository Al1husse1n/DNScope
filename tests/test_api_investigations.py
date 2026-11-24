import logging
import uuid
from typing import Any

import pytest
from starlette.testclient import TestClient

from dnscope.api.main import app
from dnscope.schemas.common import AgentStatus, RiskLevel
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import RuleHit, ScoreResult
from dnscope.schemas.supervisor import SupervisorAssessment


class FakeGraph:
    def __init__(
        self,
        canned_state: dict[str, Any] | None = None,
        should_raise: bool = False,
        sleep_seconds: float = 0.0,
    ) -> None:
        self.canned_state = canned_state or {}
        self.should_raise = should_raise
        self.sleep_seconds = sleep_seconds
        self.call_count = 0

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        if self.sleep_seconds > 0:
            import asyncio

            await asyncio.sleep(self.sleep_seconds)
        if self.should_raise:
            raise RuntimeError("Fake graph error")
        return self.canned_state


def make_canned_assessment(score: int = 45, narrative: str | None = None) -> SupervisorAssessment:
    return SupervisorAssessment(
        score_result=ScoreResult(
            score=score,
            risk_level=RiskLevel.MEDIUM if score < 70 else RiskLevel.HIGH,
            rule_hits=[
                RuleHit(
                    rule_id="RULE_TEST",
                    description="Test description",
                    points=score,
                    evidence_refs=[],
                )
            ],
            total_points_before_clamp=score,
        ),
        rule_trace_explanation="Rule trace explanation",
        narrative=narrative,
        inconclusive_checks=[],
    )


def make_canned_state(domain: str = "example.com", score: int = 45) -> dict[str, Any]:
    return {
        "domain": domain,
        "dns": DNSFinding(status=AgentStatus.OK, a_records=["1.2.3.4"]),
        "registration": RegistrationFinding(status=AgentStatus.OK, registrar="Test Registrar"),
        "reputation": ReputationFinding(status=AgentStatus.OK, detections_malicious=0),
        "assessment": make_canned_assessment(score),
    }


# 1. POST /investigations?sync=true with valid domain -> 201
def test_create_investigation_success(user_client: TestClient) -> None:
    canned = make_canned_state("example.com", 45)
    app.state.graph = FakeGraph(canned_state=canned)

    response = user_client.post("/investigations?sync=true", json={"domain": "example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["domain"] == "example.com"
    assert data["normalized_domain"] == "example.com"
    assert data["assessment"]["score_result"]["score"] == 45
    assert "X-Request-ID" in response.headers


# 1b. POST /investigations?sync=true normalizes domain
def test_create_investigation_normalizes_domain(user_client: TestClient) -> None:
    canned = make_canned_state("example.com", 20)
    app.state.graph = FakeGraph(canned_state=canned)

    response = user_client.post("/investigations?sync=true", json={"domain": "EXAMPLE.COM."})
    assert response.status_code == 201
    data = response.json()
    assert data["domain"] == "EXAMPLE.COM."
    assert data["normalized_domain"] == "example.com"


# 2. POST /investigations with invalid domain -> 400, graph NOT invoked
def test_create_investigation_invalid_domain(user_client: TestClient) -> None:
    fake_graph = FakeGraph(canned_state=make_canned_state())
    app.state.graph = fake_graph

    response = user_client.post("/investigations", json={"domain": "http://foo"})
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "invalid_domain"
    assert fake_graph.call_count == 0


# 3. POST /investigations?sync=true with fake graph that hangs > timeout -> 504
def test_create_investigation_timeout(user_client: TestClient) -> None:
    app.state.graph = FakeGraph(canned_state=make_canned_state(), sleep_seconds=0.2)
    original_timeout = getattr(app.state, "investigation_timeout", 60.0)
    app.state.investigation_timeout = 0.05
    try:
        response = user_client.post("/investigations?sync=true", json={"domain": "example.com"})
        assert response.status_code == 504
        data = response.json()
        assert data.get("error") == "investigation_timeout"
    finally:
        app.state.investigation_timeout = original_timeout


# 4. POST /investigations?sync=true with fake graph returning assessment=None -> 400
def test_create_investigation_graph_error_none_assessment(user_client: TestClient) -> None:
    app.state.graph = FakeGraph(canned_state={"domain": "example.com", "assessment": None})
    response = user_client.post("/investigations?sync=true", json={"domain": "example.com"})
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "graph_error"


# 5. GET /investigations empty -> 200 {"items": [], "total": 0}
def test_list_investigations_empty(user_client: TestClient) -> None:
    response = user_client.get("/investigations")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# 6. GET /investigations after 3 inserts -> 3 items ordered DESC by created_at
def test_list_investigations_three_items(user_client: TestClient) -> None:
    for i in range(3):
        app.state.graph = FakeGraph(canned_state=make_canned_state(f"site{i}.com", i * 10))
        user_client.post("/investigations?sync=true", json={"domain": f"site{i}.com"})

    response = user_client.get("/investigations")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    # Most recent first
    assert data["items"][0]["domain"] == "site2.com"
    assert data["items"][1]["domain"] == "site1.com"
    assert data["items"][2]["domain"] == "site0.com"


# 6b. GET /investigations pagination
def test_list_investigations_pagination(user_client: TestClient) -> None:
    for i in range(5):
        app.state.graph = FakeGraph(canned_state=make_canned_state(f"page{i}.com", i * 10))
        user_client.post("/investigations?sync=true", json={"domain": f"page{i}.com"})

    response = user_client.get("/investigations?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    # Offsetting by 1 from page4, page3, page2, page1, page0 -> returns page3, page2
    assert data["items"][0]["domain"] == "page3.com"
    assert data["items"][1]["domain"] == "page2.com"


# 7. GET /investigations/{id} valid -> 200 full response
def test_get_investigation_found(user_client: TestClient) -> None:
    app.state.graph = FakeGraph(canned_state=make_canned_state("detail.com", 70))
    create_res = user_client.post("/investigations?sync=true", json={"domain": "detail.com"})
    inv_id = create_res.json()["id"]

    get_res = user_client.get(f"/investigations/{inv_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == inv_id
    assert data["domain"] == "detail.com"
    assert data["assessment"]["score_result"]["score"] == 70


# 8. GET /investigations/{uuid4()} -> 404
def test_get_investigation_not_found(user_client: TestClient) -> None:
    random_id = uuid.uuid4()
    response = user_client.get(f"/investigations/{random_id}")
    assert response.status_code == 404


# 9. GET /investigations/{malformed-uuid} -> 422
def test_get_investigation_malformed_uuid(user_client: TestClient) -> None:
    response = user_client.get("/investigations/not-a-valid-uuid")
    assert response.status_code == 422


# 10. Response header X-Request-ID present on every endpoint
def test_request_id_header_present(user_client: TestClient) -> None:
    res_health = user_client.get("/health")
    assert "X-Request-ID" in res_health.headers

    res_list = user_client.get("/investigations")
    assert "X-Request-ID" in res_list.headers


# 11. Middleware structured logging with key_id and role
def test_middleware_structured_logging(
    user_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="dnscope.api.access"):
        user_client.get("/investigations")

    access_records = [r for r in caplog.records if r.name == "dnscope.api.access"]
    assert len(access_records) == 1
    record = access_records[0]
    assert hasattr(record, "request_id")
    assert hasattr(record, "method")
    assert record.method == "GET"
    assert hasattr(record, "path")
    assert record.path == "/investigations"
    assert hasattr(record, "status")
    assert record.status == 200
    assert hasattr(record, "duration_ms")
    assert hasattr(record, "key_id")
    assert record.key_id is not None
    assert hasattr(record, "role")
    assert record.role == "user"


# --- Tenant Isolation Tests ---


# 12. Tenant isolation: User A creates investigation, User B lists -> B sees 0
def test_tenant_isolation_list(admin_client: TestClient) -> None:
    res_a = admin_client.post("/admin/api-keys", json={"name": "user-a", "role": "user"})
    res_b = admin_client.post("/admin/api-keys", json={"name": "user-b", "role": "user"})
    key_a = res_a.json()["api_key"]
    key_b = res_b.json()["api_key"]

    app.state.graph = FakeGraph(canned_state=make_canned_state("tenant-a.com"))

    # User A creates an investigation
    create_res = admin_client.post(
        "/investigations?sync=true",
        json={"domain": "tenant-a.com"},
        headers={"X-API-Key": key_a},
    )
    assert create_res.status_code == 201

    # User B lists -> must see 0 items
    list_res = admin_client.get("/investigations", headers={"X-API-Key": key_b})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0
    assert list_res.json()["items"] == []


# 13. Tenant isolation: User B gets User A's investigation by ID -> 404 (not 403)
def test_tenant_isolation_get_returns_404(admin_client: TestClient) -> None:
    res_a = admin_client.post("/admin/api-keys", json={"name": "user-a-iso", "role": "user"})
    res_b = admin_client.post("/admin/api-keys", json={"name": "user-b-iso", "role": "user"})
    key_a = res_a.json()["api_key"]
    key_b = res_b.json()["api_key"]

    app.state.graph = FakeGraph(canned_state=make_canned_state("iso.com"))

    create_res = admin_client.post(
        "/investigations?sync=true",
        json={"domain": "iso.com"},
        headers={"X-API-Key": key_a},
    )
    inv_id = create_res.json()["id"]

    # User B requests User A's ID -> 404
    get_res = admin_client.get(f"/investigations/{inv_id}", headers={"X-API-Key": key_b})
    assert get_res.status_code == 404


# 14. Tenant isolation: Admin lists -> sees investigations from all tenants
def test_admin_lists_all_tenants(admin_client: TestClient) -> None:
    res_a = admin_client.post("/admin/api-keys", json={"name": "user-a-all", "role": "user"})
    res_b = admin_client.post("/admin/api-keys", json={"name": "user-b-all", "role": "user"})
    key_a = res_a.json()["api_key"]
    key_b = res_b.json()["api_key"]

    app.state.graph = FakeGraph(canned_state=make_canned_state("domain-a.com"))
    admin_client.post(
        "/investigations?sync=true",
        json={"domain": "domain-a.com"},
        headers={"X-API-Key": key_a},
    )

    app.state.graph = FakeGraph(canned_state=make_canned_state("domain-b.com"))
    admin_client.post(
        "/investigations?sync=true",
        json={"domain": "domain-b.com"},
        headers={"X-API-Key": key_b},
    )

    # Admin lists -> sees both
    admin_list = admin_client.get("/investigations")
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] >= 2
    domains = [item["domain"] for item in admin_list.json()["items"]]
    assert "domain-a.com" in domains
    assert "domain-b.com" in domains


# 15. Tenant isolation: Admin gets any investigation -> 200
def test_admin_gets_any_tenant(admin_client: TestClient) -> None:
    res_user = admin_client.post("/admin/api-keys", json={"name": "user-single", "role": "user"})
    user_key = res_user.json()["api_key"]

    app.state.graph = FakeGraph(canned_state=make_canned_state("admin-access.com", score=88))
    create_res = admin_client.post(
        "/investigations?sync=true",
        json={"domain": "admin-access.com"},
        headers={"X-API-Key": user_key},
    )
    inv_id = create_res.json()["id"]

    # Admin fetches user's investigation
    admin_get = admin_client.get(f"/investigations/{inv_id}")
    assert admin_get.status_code == 200
    assert admin_get.json()["domain"] == "admin-access.com"
    assert admin_get.json()["assessment"]["score_result"]["score"] == 88