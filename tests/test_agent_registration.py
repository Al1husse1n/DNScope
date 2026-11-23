import json
from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from dnscope.agents.registration import RegistrationAgent
from dnscope.schemas.common import AgentStatus

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def rdap_google_data() -> dict:
    with open(FIXTURES_DIR / "rdap_google_com.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def rdap_nonexistent_data() -> dict:
    with open(FIXTURES_DIR / "rdap_nonexistent.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_registration_200_google_fixture(
    httpx_mock: HTTPXMock, rdap_google_data: dict
) -> None:
    httpx_mock.add_response(
        url="https://rdap.org/domain/google.com",
        status_code=200,
        json=rdap_google_data,
    )
    agent = RegistrationAgent()
    finding = await agent.investigate("google.com")

    assert finding.status == AgentStatus.OK
    assert finding.registrar == "MarkMonitor Inc."
    assert finding.created_at == "1997-09-15T04:00:00Z"
    assert finding.expires_at == "2028-09-14T04:00:00Z"
    assert finding.age_days is not None
    assert finding.age_days > 0
    assert finding.errors == []
    assert finding.evidence == []
    assert finding.duration_ms is not None


@pytest.mark.asyncio
async def test_registration_200_minimal_no_entities(httpx_mock: HTTPXMock) -> None:
    body = {
        "ldhName": "minimal.com",
        "events": [
            {"eventAction": "registration", "eventDate": "2022-01-01T00:00:00Z"},
            {"eventAction": "expiration", "eventDate": "2025-01-01T00:00:00Z"},
        ],
    }
    httpx_mock.add_response(
        url="https://rdap.org/domain/minimal.com",
        status_code=200,
        json=body,
    )
    agent = RegistrationAgent()
    finding = await agent.investigate("minimal.com")

    assert finding.status == AgentStatus.OK
    assert finding.registrar is None
    assert finding.created_at == "2022-01-01T00:00:00Z"
    assert finding.expires_at == "2025-01-01T00:00:00Z"
    assert finding.age_days is not None
    assert finding.age_days > 0


@pytest.mark.asyncio
async def test_registration_200_missing_events_partial(httpx_mock: HTTPXMock) -> None:
    body = {
        "ldhName": "no-events.com",
        "entities": [],
    }
    httpx_mock.add_response(
        url="https://rdap.org/domain/no-events.com",
        status_code=200,
        json=body,
    )
    agent = RegistrationAgent()
    finding = await agent.investigate("no-events.com")

    assert finding.status == AgentStatus.PARTIAL
    assert finding.age_days is None
    assert len(finding.errors) > 0
    assert "missing events" in finding.errors[0]


@pytest.mark.asyncio
async def test_registration_404_not_found(
    httpx_mock: HTTPXMock, rdap_nonexistent_data: dict
) -> None:
    httpx_mock.add_response(
        url="https://rdap.org/domain/nonexistent.com",
        status_code=404,
        json=rdap_nonexistent_data,
    )
    agent = RegistrationAgent()
    finding = await agent.investigate("nonexistent.com")

    assert finding.status == AgentStatus.PARTIAL
    assert len(finding.errors) == 1
    assert "not found" in finding.errors[0]


@pytest.mark.asyncio
async def test_registration_500_server_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://rdap.org/domain/server-error.com",
        status_code=500,
    )
    agent = RegistrationAgent()
    finding = await agent.investigate("server-error.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "500" in finding.errors[0]


@pytest.mark.asyncio
async def test_registration_timeout_exception(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(
        httpx.ConnectTimeout("Connection timed out"),
        url="https://rdap.org/domain/timeout-domain.com",
    )
    agent = RegistrationAgent()
    finding = await agent.investigate("timeout-domain.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "timeout" in finding.errors[0].lower()


@pytest.mark.asyncio
async def test_registration_invalid_domain_no_http_calls(httpx_mock: HTTPXMock) -> None:
    agent = RegistrationAgent()
    finding = await agent.investigate("http://foo.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 1
    assert "invalid domain" in finding.errors[0].lower()
    # Assert zero HTTP calls were made
    assert httpx_mock.get_requests() == []


@pytest.mark.asyncio
async def test_registration_redirect_observed_two_requests(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://rdap.org/domain/redirected.com",
        status_code=302,
        headers={"Location": "https://registry.example.org/domain/redirected.com"},
    )
    body = {
        "ldhName": "redirected.com",
        "events": [
            {"eventAction": "registration", "eventDate": "2021-06-01T00:00:00Z"},
        ],
    }
    httpx_mock.add_response(
        url="https://registry.example.org/domain/redirected.com",
        status_code=200,
        json=body,
    )
    agent = RegistrationAgent()
    finding = await agent.investigate("redirected.com")

    assert finding.status == AgentStatus.OK
    assert finding.created_at == "2021-06-01T00:00:00Z"
    assert finding.age_days is not None
    assert finding.age_days > 0
    # Exactly two HTTP requests observed
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.asyncio
async def test_registration_never_raises_on_garbage_input() -> None:
    agent = RegistrationAgent()
    finding_none = await agent.investigate(None)  # type: ignore[arg-type]
    assert finding_none.status == AgentStatus.ERROR
    assert len(finding_none.errors) > 0

    finding_empty = await agent.investigate("   ")
    assert finding_empty.status == AgentStatus.ERROR
    assert len(finding_empty.errors) > 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_registration_live_example_com() -> None:
    agent = RegistrationAgent(timeout_seconds=8.0)
    finding = await agent.investigate("example.com")
    assert finding.status in (AgentStatus.OK, AgentStatus.PARTIAL)
    assert finding.duration_ms is not None
