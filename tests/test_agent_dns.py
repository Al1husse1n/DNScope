from typing import Any

import dns.exception
import dns.resolver
import pytest

from dnscope.agents.dns import DNSAgent
from dnscope.schemas.common import AgentStatus


class FakeRecord:
    def __init__(self, value: str) -> None:
        self._value = value

    def to_text(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value


class FakeARecord:
    def __init__(self, address: str) -> None:
        self.address = address

    def __str__(self) -> str:
        return self.address


class FakeResolver:
    def __init__(self, canned: dict[str, Any] | None = None) -> None:
        self.canned: dict[str, Any] = canned or {}

    async def resolve(self, qname: str, rdtype: str) -> list[Any]:
        result = self.canned.get(rdtype, [])
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.asyncio
async def test_dns_all_five_succeed() -> None:
    canned = {
        "A": [FakeARecord("93.184.216.34")],
        "AAAA": [FakeARecord("2606:2800:220:1:248:1893:25c8:1946")],
        "MX": [FakeRecord("10 mail.example.com.")],
        "NS": [FakeRecord("ns1.example.com."), FakeRecord("ns2.example.com.")],
        "TXT": [FakeRecord('"v=spf1 include:_spf.example.com ~all"')],
    }
    agent = DNSAgent(resolver=FakeResolver(canned))
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.OK
    assert finding.a_records == ["93.184.216.34"]
    assert finding.aaaa_records == ["2606:2800:220:1:248:1893:25c8:1946"]
    assert finding.mx_records == ["10 mail.example.com"]
    assert finding.ns_records == ["ns1.example.com", "ns2.example.com"]
    assert finding.has_spf is True
    assert finding.errors == []
    assert finding.evidence == []
    assert finding.duration_ms is not None
    assert finding.duration_ms >= 0


@pytest.mark.asyncio
async def test_dns_all_five_succeed_empty_answers() -> None:
    canned = {
        "A": [FakeARecord("93.184.216.34")],
        "AAAA": [],
        "MX": [FakeRecord("mail.example.com")],
        "NS": [],
        "TXT": [],
    }
    agent = DNSAgent(resolver=FakeResolver(canned))
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.OK
    assert finding.a_records == ["93.184.216.34"]
    assert finding.aaaa_records == []
    assert finding.ns_records == []
    assert finding.mx_records == ["mail.example.com"]
    assert finding.has_spf is False
    assert finding.errors == []


@pytest.mark.asyncio
async def test_dns_mx_raises_nxdomain_partial() -> None:
    canned = {
        "A": [FakeARecord("93.184.216.34")],
        "AAAA": [FakeARecord("2606:2800:220:1:248:1893:25c8:1946")],
        "MX": dns.resolver.NXDOMAIN(),
        "NS": [FakeRecord("ns1.example.com")],
        "TXT": [FakeRecord("v=spf1 -all")],
    }
    agent = DNSAgent(resolver=FakeResolver(canned))
    finding = await agent.investigate("example.com")

    assert finding.status == AgentStatus.PARTIAL
    assert len(finding.errors) == 1
    assert "MX" in finding.errors[0]
    assert "NXDOMAIN" in finding.errors[0]
    assert finding.a_records == ["93.184.216.34"]


@pytest.mark.asyncio
async def test_dns_all_lookups_raise_error() -> None:
    canned = {
        "A": dns.resolver.NXDOMAIN(),
        "AAAA": dns.resolver.NXDOMAIN(),
        "MX": dns.resolver.NXDOMAIN(),
        "NS": dns.resolver.NXDOMAIN(),
        "TXT": dns.resolver.NXDOMAIN(),
    }
    agent = DNSAgent(resolver=FakeResolver(canned))
    finding = await agent.investigate("nonexistent.invalid")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 5
    assert finding.has_spf is None
    assert finding.duration_ms is not None


@pytest.mark.asyncio
async def test_dns_resolver_timeout_all_error() -> None:
    canned = {
        "A": dns.exception.Timeout(),
        "AAAA": dns.exception.Timeout(),
        "MX": dns.exception.Timeout(),
        "NS": dns.exception.Timeout(),
        "TXT": dns.exception.Timeout(),
    }
    agent = DNSAgent(resolver=FakeResolver(canned))
    finding = await agent.investigate("timeout.example.com")

    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) == 5
    assert all("Timeout" in err for err in finding.errors)
    assert finding.has_spf is None


@pytest.mark.asyncio
async def test_dns_txt_succeeds_no_spf() -> None:
    canned = {
        "A": [FakeARecord("1.1.1.1")],
        "AAAA": [],
        "MX": [],
        "NS": [FakeRecord("ns1.cloudflare.com")],
        "TXT": [FakeRecord("google-site-verification=abc123xyz")],
    }
    agent = DNSAgent(resolver=FakeResolver(canned))
    finding = await agent.investigate("cloudflare.com")

    assert finding.status == AgentStatus.OK
    assert finding.has_spf is False


@pytest.mark.asyncio
async def test_dns_txt_fails_has_spf_none() -> None:
    canned = {
        "A": [FakeARecord("1.1.1.1")],
        "AAAA": [],
        "MX": [],
        "NS": [FakeRecord("ns1.cloudflare.com")],
        "TXT": dns.resolver.NoAnswer(),
    }
    agent = DNSAgent(resolver=FakeResolver(canned))
    finding = await agent.investigate("cloudflare.com")

    assert finding.status == AgentStatus.PARTIAL
    assert finding.has_spf is None
    assert any("TXT" in err for err in finding.errors)


@pytest.mark.asyncio
async def test_dns_duration_ms_populated_on_ok_and_error() -> None:
    ok_agent = DNSAgent(resolver=FakeResolver({"A": [FakeARecord("1.2.3.4")]}))
    ok_finding = await ok_agent.investigate("example.com")
    assert ok_finding.duration_ms is not None
    assert ok_finding.duration_ms >= 0

    err_agent = DNSAgent(
        resolver=FakeResolver(
            {
                "A": dns.resolver.NXDOMAIN(),
                "AAAA": dns.resolver.NXDOMAIN(),
                "MX": dns.resolver.NXDOMAIN(),
                "NS": dns.resolver.NXDOMAIN(),
                "TXT": dns.resolver.NXDOMAIN(),
            }
        )
    )
    err_finding = await err_agent.investigate("example.com")
    assert err_finding.duration_ms is not None
    assert err_finding.duration_ms >= 0


@pytest.mark.asyncio
async def test_dns_never_raises_on_invalid_input() -> None:
    agent = DNSAgent()
    # Garbage input
    finding = await agent.investigate("http://invalid:8080/path")
    assert finding.status == AgentStatus.ERROR
    assert len(finding.errors) > 0
    assert "Invalid domain" in finding.errors[0]
    assert finding.duration_ms is not None

    finding_none = await agent.investigate(None)  # type: ignore[arg-type]
    assert finding_none.status == AgentStatus.ERROR
    assert len(finding_none.errors) > 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_dns_live_lookup_example_com() -> None:
    agent = DNSAgent(timeout_seconds=5.0)
    finding = await agent.investigate("example.com")
    assert finding.status in (AgentStatus.OK, AgentStatus.PARTIAL)
    assert len(finding.a_records) > 0
    assert finding.duration_ms is not None
