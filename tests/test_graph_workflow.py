import asyncio
import time
from typing import Any

import pytest

from dnscope.graph.workflow import build_investigation_graph
from dnscope.schemas.common import AgentStatus, RiskLevel
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding


class FakeAgent:
    def __init__(
        self,
        canned_finding: Any,
        sleep_seconds: float = 0.0,
        should_raise: Exception | None = None,
    ) -> None:
        self.canned = canned_finding
        self.sleep_seconds = sleep_seconds
        self.should_raise = should_raise
        self.calls: list[str] = []

    async def investigate(self, domain: str) -> Any:
        self.calls.append(domain)
        if self.sleep_seconds > 0:
            await asyncio.sleep(self.sleep_seconds)
        if self.should_raise is not None:
            raise self.should_raise
        return self.canned


# 12. Happy path
@pytest.mark.asyncio
async def test_graph_happy_path() -> None:
    dns_fake = FakeAgent(DNSFinding(status=AgentStatus.OK, a_records=["1.2.3.4"]))
    reg_fake = FakeAgent(RegistrationFinding(status=AgentStatus.OK, age_days=100))
    rep_fake = FakeAgent(
        ReputationFinding(status=AgentStatus.OK, detections_malicious=0, total_engines=70)
    )

    graph = build_investigation_graph(
        dns_agent=dns_fake,  # type: ignore[arg-type]
        registration_agent=reg_fake,  # type: ignore[arg-type]
        reputation_agent=rep_fake,  # type: ignore[arg-type]
    )

    result = await graph.ainvoke({"domain": "example.com"})

    assert result["domain"] == "example.com"
    assert result["normalized_domain"] == "example.com"
    assert result["assessment"] is not None
    assert result["assessment"].score_result.risk_level == RiskLevel.LOW
    assert len(dns_fake.calls) == 1
    assert len(reg_fake.calls) == 1
    assert len(rep_fake.calls) == 1


# 13. Validation failure short-circuits to END without invoking agents
@pytest.mark.asyncio
async def test_graph_validation_failure() -> None:
    dns_fake = FakeAgent(DNSFinding(status=AgentStatus.OK))
    reg_fake = FakeAgent(RegistrationFinding(status=AgentStatus.OK))
    rep_fake = FakeAgent(ReputationFinding(status=AgentStatus.OK))

    graph = build_investigation_graph(
        dns_agent=dns_fake,  # type: ignore[arg-type]
        registration_agent=reg_fake,  # type: ignore[arg-type]
        reputation_agent=rep_fake,  # type: ignore[arg-type]
    )

    result = await graph.ainvoke({"domain": "not a domain"})

    assert result["domain"] == "not a domain"
    assert result["normalized_domain"] == ""
    assert result.get("assessment") is None

    # Prove agents were never called
    assert dns_fake.calls == []
    assert reg_fake.calls == []
    assert rep_fake.calls == []


# 14. Parallelism timing test
@pytest.mark.asyncio
async def test_graph_parallelism_timing() -> None:
    dns_fake = FakeAgent(DNSFinding(status=AgentStatus.OK), sleep_seconds=0.3)
    reg_fake = FakeAgent(RegistrationFinding(status=AgentStatus.OK), sleep_seconds=0.3)
    rep_fake = FakeAgent(ReputationFinding(status=AgentStatus.OK), sleep_seconds=0.3)

    graph = build_investigation_graph(
        dns_agent=dns_fake,  # type: ignore[arg-type]
        registration_agent=reg_fake,  # type: ignore[arg-type]
        reputation_agent=rep_fake,  # type: ignore[arg-type]
    )

    t0 = time.perf_counter()
    result = await graph.ainvoke({"domain": "example.com"})
    elapsed = time.perf_counter() - t0

    assert result["assessment"] is not None
    # Parallel execution of 3x 0.3s sleep should take < 0.6s (vs > 0.9s sequential)
    assert elapsed < 0.6, f"Expected parallel elapsed < 0.6s, but got {elapsed:.3f}s"


# 15. One agent raises (defense in depth)
@pytest.mark.asyncio
async def test_graph_one_agent_raises_defense_in_depth() -> None:
    dns_fake = FakeAgent(None, should_raise=RuntimeError("boom"))
    reg_fake = FakeAgent(RegistrationFinding(status=AgentStatus.OK, age_days=100))
    rep_fake = FakeAgent(
        ReputationFinding(status=AgentStatus.OK, detections_malicious=0, total_engines=70)
    )

    graph = build_investigation_graph(
        dns_agent=dns_fake,  # type: ignore[arg-type]
        registration_agent=reg_fake,  # type: ignore[arg-type]
        reputation_agent=rep_fake,  # type: ignore[arg-type]
    )

    result = await graph.ainvoke({"domain": "example.com"})

    assert result["assessment"] is not None
    inconclusive_names = [c.agent_name for c in result["assessment"].inconclusive_checks]
    assert "dns" in inconclusive_names
    assert result["assessment"].score_result is not None


# 16. Two agents raise
@pytest.mark.asyncio
async def test_graph_two_agents_raise() -> None:
    dns_fake = FakeAgent(None, should_raise=RuntimeError("DNS crash"))
    reg_fake = FakeAgent(None, should_raise=ConnectionError("RDAP timeout"))
    rep_fake = FakeAgent(
        ReputationFinding(status=AgentStatus.OK, detections_malicious=0, total_engines=70)
    )

    graph = build_investigation_graph(
        dns_agent=dns_fake,  # type: ignore[arg-type]
        registration_agent=reg_fake,  # type: ignore[arg-type]
        reputation_agent=rep_fake,  # type: ignore[arg-type]
    )

    result = await graph.ainvoke({"domain": "example.com"})

    assert result["assessment"] is not None
    inconclusive_names = [c.agent_name for c in result["assessment"].inconclusive_checks]
    assert "dns" in inconclusive_names
    assert "registration" in inconclusive_names
    assert "reputation" not in inconclusive_names


# 17. All three agents raise
@pytest.mark.asyncio
async def test_graph_all_three_agents_raise() -> None:
    dns_fake = FakeAgent(None, should_raise=RuntimeError("DNS fail"))
    reg_fake = FakeAgent(None, should_raise=RuntimeError("RDAP fail"))
    rep_fake = FakeAgent(None, should_raise=RuntimeError("VT fail"))

    graph = build_investigation_graph(
        dns_agent=dns_fake,  # type: ignore[arg-type]
        registration_agent=reg_fake,  # type: ignore[arg-type]
        reputation_agent=rep_fake,  # type: ignore[arg-type]
    )

    result = await graph.ainvoke({"domain": "example.com"})

    assert result["assessment"] is not None
    inconclusive_names = [c.agent_name for c in result["assessment"].inconclusive_checks]
    assert set(inconclusive_names) == {"dns", "registration", "reputation"}
    assert result["assessment"].score_result.score == 0
    assert result["assessment"].score_result.risk_level == RiskLevel.LOW


# 18. Domain normalized before agents
@pytest.mark.asyncio
async def test_graph_domain_normalized_before_agents() -> None:
    dns_fake = FakeAgent(DNSFinding(status=AgentStatus.OK))
    reg_fake = FakeAgent(RegistrationFinding(status=AgentStatus.OK))
    rep_fake = FakeAgent(ReputationFinding(status=AgentStatus.OK))

    graph = build_investigation_graph(
        dns_agent=dns_fake,  # type: ignore[arg-type]
        registration_agent=reg_fake,  # type: ignore[arg-type]
        reputation_agent=rep_fake,  # type: ignore[arg-type]
    )

    result = await graph.ainvoke({"domain": "EXAMPLE.COM."})

    assert result["normalized_domain"] == "example.com"
    assert dns_fake.calls == ["example.com"]
    assert reg_fake.calls == ["example.com"]
    assert rep_fake.calls == ["example.com"]


# 19. New compiled graph per call
def test_graph_new_compiled_graph_per_call() -> None:
    g1 = build_investigation_graph()
    g2 = build_investigation_graph()
    assert g1 is not g2
