import asyncio
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
        sleep_seconds: float = 0.0,
    ) -> None:
        self.canned_state = canned_state
        self.sleep_seconds = sleep_seconds
        self.call_count = 0
        self.last_state: dict[str, Any] | None = None

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        self.last_state = state
        if self.sleep_seconds > 0:
            await asyncio.sleep(self.sleep_seconds)
        if self.canned_state is not None:
            return dict(self.canned_state)
        return {}


def make_canned_assessment(
    score: int = 45, narrative: str = "Canned narrative"
) -> SupervisorAssessment:
    return SupervisorAssessment(
        score_result=ScoreResult(
            score=score,
            risk_level=RiskLevel.MEDIUM,
            rule_hits=[
                RuleHit(
                    rule_id="RULE_TEST",
                    description="Test rule description",
                    points=score,
                    evidence_refs=["ref1"],
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


# 1. POST /investigations with valid domain -> 201
def test_create_investigation_success(client: TestClient) -> None:
    canned = make_canned_state("example.com", 45)
    app.state.graph = FakeGraph(canned_state=canned)

    response = client.post("/investigations", json={"domain": "example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["domain"] == "example.com"
    assert data["normalized_domain"] == "example.com"
    assert data["assessment"]["score_result"]["score"] == 45
    assert "X-Request-ID" in response.headers


# 1b. POST /investigations normalizes domain
def test_create_investigation_normalizes_domain(client: TestClient) -> None:
    canned = make_canned_state("example.com", 20)
    app.state.graph = FakeGraph(canned_state=canned)

    response = client.post("/investigations", json={"domain": "EXAMPLE.COM."})
    assert response.status_code == 201
    data = response.json()
    assert data["domain"] == "EXAMPLE.COM."
    assert data["normalized_domain"] == "example.com"


# 2. POST /investigations with invalid domain -> 400, graph NOT invoked
def test_create_investigation_invalid_domain(client: TestClient) -> None:
    fake_graph = FakeGraph(canned_state=make_canned_state())
    app.state.graph = fake_graph

    response = client.post("/investigations", json={"domain": "http://foo"})
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "invalid_domain"
    assert fake_graph.call_count == 0


# 3. POST /investigations with fake graph that hangs > timeout -> 504
def test_create_investigation_timeout(client: TestClient) -> None:
    app.state.graph = FakeGraph(canned_state=make_canned_state(), sleep_seconds=0.2)
    original_timeout = getattr(app.state, "investigation_timeout", 60.0)
    app.state.investigation_timeout = 0.05
    try:
        response = client.post("/investigations", json={"domain": "example.com"})
        assert response.status_code == 504
        data = response.json()
        assert data.get("error") == "investigation_timeout"
    finally:
        app.state.investigation_timeout = original_timeout


# 4. POST /investigations with fake graph returning assessment=None -> 400
def test_create_investigation_graph_error_none_assessment(client: TestClient) -> None:
    app.state.graph = FakeGraph(canned_state={"domain": "example.com", "assessment": None})
    response = client.post("/investigations", json={"domain": "example.com"})
    assert response.status_code == 400
    data = response.json()
    assert data.get("error") == "graph_error"


# 4b. POST /investigations saves partial findings when agents report error
def test_create_investigation_partial_findings_saved_on_agent_failure(
    client: TestClient,
) -> None:
    canned = {
        "domain": "partial.com",
        "dns": DNSFinding(status=AgentStatus.ERROR, error="DNS timeout"),
        "registration": RegistrationFinding(status=AgentStatus.OK, registrar="Safe Registrar"),
        "reputation": ReputationFinding(status=AgentStatus.ERROR, error="Rate limited"),
        "assessment": make_canned_assessment(10),
    }
    app.state.graph = FakeGraph(canned_state=canned)

    response = client.post("/investigations", json={"domain": "partial.com"})
    assert response.status_code == 201
    data = response.json()
    assert data["findings"]["dns"]["status"] == "error"
    assert data["findings"]["dns"]["error"] == "DNS timeout"
    assert data["findings"]["registration"]["status"] == "ok"
    assert data["findings"]["reputation"]["status"] == "error"


# 5. GET /investigations empty -> 200 {"items": [], "total": 0}
def test_list_investigations_empty(client: TestClient) -> None:
    response = client.get("/investigations")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# 6. GET /investigations after 3 inserts -> 3 items ordered DESC by created_at
def test_list_investigations_three_items(client: TestClient) -> None:
    for i in range(3):
        app.state.graph = FakeGraph(canned_state=make_canned_state(f"site{i}.com", i * 10))
        client.post("/investigations", json={"domain": f"site{i}.com"})

    response = client.get("/investigations")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    # Most recent first
    assert data["items"][0]["domain"] == "site2.com"
    assert data["items"][1]["domain"] == "site1.com"
    assert data["items"][2]["domain"] == "site0.com"


# 6b. GET /investigations pagination
def test_list_investigations_pagination(client: TestClient) -> None:
    for i in range(5):
        app.state.graph = FakeGraph(canned_state=make_canned_state(f"page{i}.com", i * 10))
        client.post("/investigations", json={"domain": f"page{i}.com"})

    response = client.get("/investigations?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    # Offsetting by 1 from page4, page3, page2, page1, page0 -> returns page3, page2
    assert data["items"][0]["domain"] == "page3.com"
    assert data["items"][1]["domain"] == "page2.com"


# 7. GET /investigations/{id} valid -> 200 full response
def test_get_investigation_found(client: TestClient) -> None:
    app.state.graph = FakeGraph(canned_state=make_canned_state("detail.com", 70))
    create_res = client.post("/investigations", json={"domain": "detail.com"})
    inv_id = create_res.json()["id"]

    get_res = client.get(f"/investigations/{inv_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == inv_id
    assert data["domain"] == "detail.com"
    assert data["assessment"]["score_result"]["score"] == 70


# 8. GET /investigations/{uuid4()} -> 404
def test_get_investigation_not_found(client: TestClient) -> None:
    random_id = uuid.uuid4()
    response = client.get(f"/investigations/{random_id}")
    assert response.status_code == 404


# 9. GET /investigations/{malformed-uuid} -> 422
def test_get_investigation_malformed_uuid(client: TestClient) -> None:
    response = client.get("/investigations/not-a-valid-uuid")
    assert response.status_code == 422


# 10. Response header X-Request-ID present on every endpoint
def test_request_id_header_present(client: TestClient) -> None:
    res_health = client.get("/health")
    assert "X-Request-ID" in res_health.headers

    res_list = client.get("/investigations")
    assert "X-Request-ID" in res_list.headers


# 12. Middleware logging test
def test_middleware_structured_logging(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="dnscope.api.access"):
        client.get("/health")

    access_records = [r for r in caplog.records if r.name == "dnscope.api.access"]
    assert len(access_records) == 1
    record = access_records[0]
    assert hasattr(record, "request_id")
    assert hasattr(record, "method")
    assert record.method == "GET"
    assert hasattr(record, "path")
    assert record.path == "/health"
    assert hasattr(record, "status")
    assert record.status == 200
    assert hasattr(record, "duration_ms")