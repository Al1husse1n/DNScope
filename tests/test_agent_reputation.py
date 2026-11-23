import inspect
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from dnscope.agents.base import InvestigationAgent
from dnscope.agents.reputation import ReputationAgent
from dnscope.schemas.common import AgentStatus

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def vt_malicious_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "vt_domain_malicious.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def vt_clean_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "vt_domain_clean.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def vt_404_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "vt_domain_404.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def vt_401_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "vt_domain_401.json", encoding="utf-8") as f:
        return json.load(f)


# 1. Happy path: Malicious domain
@pytest.mark.asyncio
async def test_reputation_malicious_domain(
    httpx_mock: HTTPXMock, vt_malicious_data: dict[str, Any]
) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/malicious.example.com",
        status_code=200,
        json=vt_malicious_data,
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("malicious.example.com")

    assert finding.status == AgentStatus.OK
    assert finding.detections_malicious is not None
    assert finding.detections_malicious >= 5
    assert finding.detections_suspicious == 3
    assert finding.total_engines is not None
    assert finding.total_engines > 0
    assert len(finding.categories) > 0
    assert "malicious" in finding.categories
    assert finding.permalink == "https://www.virustotal.com/api/v3/domains/malicious.example.com"
    assert finding.errors == []
    assert finding.evidence == []
    assert finding.duration_ms is not None


# 2. Happy path: Clean domain
@pytest.mark.asyncio
async def test_reputation_clean_domain(
    httpx_mock: HTTPXMock, vt_clean_data: dict[str, Any]
) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/clean.example.com",
        status_code=200,
        json=vt_clean_data,
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("clean.example.com")

    assert finding.status == AgentStatus.OK
    assert finding.detections_malicious == 0
    assert finding.detections_suspicious == 0
    assert finding.total_engines == 70
    assert finding.categories == ["business"]
    assert finding.permalink == "https://www.virustotal.com/api/v3/domains/clean.example.com"


# 3. Happy path: Sparse body
@pytest.mark.asyncio
async def test_reputation_sparse_body(httpx_mock: HTTPXMock) -> None:
    sparse_data = {
        "data": {
            "attributes": {
                "last_analysis_stats": {
                    "harmless": 20,
                    "malicious": 2,
                    "suspicious": 1,
                    "undetected": 10,
                }
            }
        }
    }
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/sparse.com",
        status_code=200,
        json=sparse_data,
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("sparse.com")

    assert finding.status == AgentStatus.OK
    assert finding.detections_malicious == 2
    assert finding.detections_suspicious == 1
    assert finding.total_engines == 33
    assert finding.categories == []
    assert finding.permalink is None


# 4. Pre-flight: Missing API key (None)
@pytest.mark.asyncio
async def test_reputation_missing_api_key_none(httpx_mock: HTTPXMock) -> None:
    agent = ReputationAgent(api_key=None)
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.SKIPPED
    assert finding.errors == ["missing VT_API_KEY"]
    assert httpx_mock.get_requests() == []


# 5. Pre-flight: Empty API key ("")
@pytest.mark.asyncio
async def test_reputation_empty_api_key(httpx_mock: HTTPXMock) -> None:
    agent = ReputationAgent(api_key="")
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.SKIPPED
    assert finding.errors == ["missing VT_API_KEY"]
    assert httpx_mock.get_requests() == []


# 6. Pre-flight: Invalid domain
@pytest.mark.asyncio
async def test_reputation_invalid_domain(httpx_mock: HTTPXMock) -> None:
    agent = ReputationAgent(api_key="valid-key")
    finding = await agent.investigate("http://foo.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "invalid domain" in finding.errors[0].lower()
    assert httpx_mock.get_requests() == []


# 7. Error mapping: 404
@pytest.mark.asyncio
async def test_reputation_404_not_found(httpx_mock: HTTPXMock, vt_404_data: dict[str, Any]) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/nonexistent.com",
        status_code=404,
        json=vt_404_data,
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("nonexistent.com")

    assert finding.status == AgentStatus.PARTIAL
    assert finding.detections_malicious is None
    assert finding.detections_suspicious is None
    assert finding.total_engines is None
    assert finding.categories == []
    assert finding.permalink is None
    assert len(finding.errors) == 1
    assert "not found" in finding.errors[0].lower()


# 8. Error mapping: 401
@pytest.mark.asyncio
async def test_reputation_401_auth_failed(
    httpx_mock: HTTPXMock, vt_401_data: dict[str, Any]
) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/example.com",
        status_code=401,
        json=vt_401_data,
    )
    agent = ReputationAgent(api_key="wrong-key")
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.ERROR
    assert finding.detections_malicious is None
    assert len(finding.errors) == 1
    assert "auth failed" in finding.errors[0].lower()


# 9. Error mapping: 403
@pytest.mark.asyncio
async def test_reputation_403_auth_failed(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/example.com",
        status_code=403,
    )
    agent = ReputationAgent(api_key="forbidden-key")
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.ERROR
    assert finding.detections_malicious is None
    assert len(finding.errors) == 1
    assert "auth failed" in finding.errors[0].lower()


# 10. Error mapping: 429
@pytest.mark.asyncio
async def test_reputation_429_rate_limit(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/example.com",
        status_code=429,
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "rate limit" in finding.errors[0].lower()


# 11. Error mapping: 500
@pytest.mark.asyncio
async def test_reputation_500_server_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/example.com",
        status_code=500,
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "500" in finding.errors[0]


# 12. Error mapping: Timeout
@pytest.mark.asyncio
async def test_reputation_timeout_exception(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(
        httpx.ConnectTimeout("Connect timeout"),
        url="https://www.virustotal.com/api/v3/domains/example.com",
    )
    agent = ReputationAgent(api_key="test-api-key", timeout_seconds=5.0)
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "timeout" in finding.errors[0].lower()


# 13. Error mapping: Malformed JSON
@pytest.mark.asyncio
async def test_reputation_malformed_json(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/example.com",
        status_code=200,
        content=b"not-json-content",
        headers={"content-type": "application/json"},
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "malformed" in finding.errors[0].lower()


# 14. Safety & invariants: API key never leaked
@pytest.mark.asyncio
async def test_reputation_api_key_never_leaked(
    httpx_mock: HTTPXMock, vt_401_data: dict[str, Any]
) -> None:
    secret_key = "secret_vt_key_99999_xyz"
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/example.com",
        status_code=401,
        json=vt_401_data,
    )
    agent = ReputationAgent(api_key=secret_key)
    assert secret_key not in repr(agent)
    assert secret_key not in str(agent)

    finding = await agent.investigate("example.com")
    dumped_json = finding.model_dump_json()

    assert secret_key not in dumped_json
    for err in finding.errors:
        assert secret_key not in err


# 15. Safety & invariants: Endpoint lock-in
@pytest.mark.asyncio
async def test_reputation_endpoint_lock_in(
    httpx_mock: HTTPXMock, vt_clean_data: dict[str, Any]
) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/test-lockin.com",
        status_code=200,
        json=vt_clean_data,
    )
    agent = ReputationAgent(api_key="test-api-key")
    finding = await agent.investigate("test-lockin.com")

    assert finding.status == AgentStatus.OK
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert str(requests[0].url) == "https://www.virustotal.com/api/v3/domains/test-lockin.com"
    assert requests[0].method == "GET"
    assert requests[0].headers.get("x-apikey") == "test-api-key"


# 16. Safety & invariants: Never-raise on garbage input
@pytest.mark.asyncio
async def test_reputation_never_raise_on_garbage() -> None:
    agent = ReputationAgent(api_key="test-key")
    finding_none = await agent.investigate(None)  # type: ignore[arg-type]
    assert finding_none.status == AgentStatus.ERROR
    assert len(finding_none.errors) > 0

    finding_num = await agent.investigate(123)  # type: ignore[arg-type]
    assert finding_num.status == AgentStatus.ERROR
    assert len(finding_num.errors) > 0


# 17. Safety & invariants: Injected client not closed
@pytest.mark.asyncio
async def test_reputation_injected_client_not_closed(
    httpx_mock: HTTPXMock, vt_clean_data: dict[str, Any]
) -> None:
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/client-test.com",
        status_code=200,
        json=vt_clean_data,
    )
    injected_client = httpx.AsyncClient()
    agent = ReputationAgent(api_key="test-key", http_client=injected_client)

    finding = await agent.investigate("client-test.com")
    assert finding.status == AgentStatus.OK
    assert injected_client.is_closed is False
    await injected_client.aclose()


# 18. Invariants: total_engines None vs 0 distinction
@pytest.mark.asyncio
async def test_reputation_total_engines_none_vs_zero(httpx_mock: HTTPXMock) -> None:
    # Case A: last_analysis_stats missing -> total_engines is None
    body_no_stats = {"data": {"attributes": {}}}
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/no-stats.com",
        status_code=200,
        json=body_no_stats,
    )
    agent = ReputationAgent(api_key="test-key")
    finding_a = await agent.investigate("no-stats.com")
    assert finding_a.status == AgentStatus.OK
    assert finding_a.total_engines is None

    # Case B: last_analysis_stats empty dict -> total_engines is None
    body_empty_stats = {"data": {"attributes": {"last_analysis_stats": {}}}}
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/empty-stats.com",
        status_code=200,
        json=body_empty_stats,
    )
    finding_b = await agent.investigate("empty-stats.com")
    assert finding_b.status == AgentStatus.OK
    assert finding_b.total_engines is None

    # Case C: last_analysis_stats present with all 0s -> total_engines == 0
    body_zero_stats = {
        "data": {
            "attributes": {
                "last_analysis_stats": {
                    "harmless": 0,
                    "malicious": 0,
                    "suspicious": 0,
                    "undetected": 0,
                }
            }
        }
    }
    httpx_mock.add_response(
        url="https://www.virustotal.com/api/v3/domains/zero-stats.com",
        status_code=200,
        json=body_zero_stats,
    )
    finding_c = await agent.investigate("zero-stats.com")
    assert finding_c.status == AgentStatus.OK
    assert finding_c.total_engines == 0


# 19. Protocol conformance: implements InvestigationAgent protocol
def test_reputation_implements_investigation_agent_protocol() -> None:
    agent: InvestigationAgent = ReputationAgent()
    assert hasattr(agent, "investigate")
    assert callable(agent.investigate)
    assert inspect.iscoroutinefunction(agent.investigate)


# 20. Live test: against google.com (skipped if VT_API_KEY is unset)
@pytest.mark.live
@pytest.mark.skipif(not os.getenv("VT_API_KEY"), reason="VT_API_KEY not set")
@pytest.mark.asyncio
async def test_reputation_live_google_com() -> None:
    api_key = os.getenv("VT_API_KEY")
    agent = ReputationAgent(api_key=api_key)
    finding = await agent.investigate("google.com")
    assert finding.status in (AgentStatus.OK, AgentStatus.PARTIAL)
    assert finding.duration_ms is not None
