from datetime import datetime

from dnscope.schemas.common import AgentStatus, Evidence, EvidenceCategory, RiskLevel
from dnscope.schemas.findings import (
    BaseAgentFinding,
    DNSFinding,
    RegistrationFinding,
    ReputationFinding,
)
from dnscope.schemas.investigation import InvestigationFindings, InvestigationState
from dnscope.schemas.scoring import RuleHit, ScoreResult


def test_risk_level_values() -> None:
    assert RiskLevel.LOW.value == "LOW"
    assert RiskLevel.MEDIUM.value == "MEDIUM"
    assert RiskLevel.HIGH.value == "HIGH"
    assert RiskLevel.CRITICAL.value == "CRITICAL"


def test_agent_status_values() -> None:
    assert AgentStatus.OK.value == "OK"
    assert AgentStatus.PARTIAL.value == "PARTIAL"
    assert AgentStatus.ERROR.value == "ERROR"
    assert AgentStatus.SKIPPED.value == "SKIPPED"


def test_evidence_category_values() -> None:
    assert EvidenceCategory.MALICIOUS.value == "MALICIOUS"
    assert EvidenceCategory.SUSPICIOUS.value == "SUSPICIOUS"
    assert EvidenceCategory.BENIGN.value == "BENIGN"
    assert EvidenceCategory.INCONCLUSIVE.value == "INCONCLUSIVE"


def test_evidence_minimal_and_roundtrip() -> None:
    evidence = Evidence(
        category=EvidenceCategory.SUSPICIOUS,
        label="test_label",
        detail="test detail message",
        source="rdap",
    )
    assert evidence.category == EvidenceCategory.SUSPICIOUS
    assert evidence.label == "test_label"
    assert evidence.detail == "test detail message"
    assert evidence.source == "rdap"
    assert isinstance(evidence.timestamp, datetime)

    dumped = evidence.model_dump()
    loaded = Evidence.model_validate(dumped)
    assert loaded.category == evidence.category
    assert loaded.label == evidence.label
    assert loaded.detail == evidence.detail
    assert loaded.source == evidence.source


def test_base_agent_finding_minimal_and_defaults() -> None:
    finding = BaseAgentFinding(
        agent_name="base_agent",
        status=AgentStatus.OK,
    )
    assert finding.agent_name == "base_agent"
    assert finding.status == AgentStatus.OK
    assert finding.errors == []
    assert finding.evidence == []
    assert finding.duration_ms is None

    dumped = finding.model_dump()
    loaded = BaseAgentFinding.model_validate(dumped)
    assert loaded.agent_name == "base_agent"
    assert loaded.status == AgentStatus.OK
    assert loaded.errors == []
    assert loaded.evidence == []


def test_dns_finding_defaults_and_roundtrip() -> None:
    dns = DNSFinding(status=AgentStatus.OK)
    assert dns.agent_name == "dns"
    assert dns.a_records == []
    assert dns.aaaa_records == []
    assert dns.mx_records == []
    assert dns.txt_records == []
    assert dns.ns_records == []
    assert dns.has_spf is None
    assert dns.errors == []

    populated = DNSFinding(
        status=AgentStatus.OK,
        a_records=["1.1.1.1"],
        aaaa_records=["2606:4700:4700::1111"],
        mx_records=["mail.cloudflare.com"],
        txt_records=["v=spf1 -all"],
        ns_records=["ns1.cloudflare.com"],
        has_spf=True,
        duration_ms=120,
    )
    dumped = populated.model_dump()
    loaded = DNSFinding.model_validate(dumped)
    assert loaded == populated


def test_registration_finding_defaults_and_roundtrip() -> None:
    reg = RegistrationFinding(status=AgentStatus.OK)
    assert reg.agent_name == "registration"
    assert reg.created_at is None
    assert reg.expires_at is None
    assert reg.registrar is None
    assert reg.age_days is None

    populated = RegistrationFinding(
        status=AgentStatus.OK,
        created_at="2020-01-01T00:00:00Z",
        expires_at="2025-01-01T00:00:00Z",
        registrar="GoDaddy",
        age_days=1500,
        duration_ms=250,
    )
    dumped = populated.model_dump()
    loaded = RegistrationFinding.model_validate(dumped)
    assert loaded == populated


def test_reputation_finding_defaults_and_roundtrip() -> None:
    rep = ReputationFinding(status=AgentStatus.OK)
    assert rep.agent_name == "reputation"
    assert rep.detections_malicious is None
    assert rep.detections_suspicious is None
    assert rep.total_engines is None
    assert rep.categories == []
    assert rep.permalink is None

    populated = ReputationFinding(
        status=AgentStatus.OK,
        detections_malicious=5,
        detections_suspicious=1,
        total_engines=85,
        categories=["malware", "phishing"],
        permalink="https://virustotal.com/gui/domain/test.com",
        duration_ms=300,
    )
    dumped = populated.model_dump()
    loaded = ReputationFinding.model_validate(dumped)
    assert loaded == populated


def test_rule_hit_and_score_result_roundtrip() -> None:
    hit = RuleHit(
        rule_id="DOMAIN_AGE_UNDER_7D",
        description="Fresh domain",
        points=30,
        evidence_refs=["domain_age_under_7d"],
    )
    assert hit.rule_id == "DOMAIN_AGE_UNDER_7D"
    assert hit.points == 30
    assert hit.evidence_refs == ["domain_age_under_7d"]

    score_result = ScoreResult(
        score=30,
        risk_level=RiskLevel.MEDIUM,
        rule_hits=[hit],
        total_points_before_clamp=30,
    )
    assert score_result.score == 30
    assert score_result.risk_level == RiskLevel.MEDIUM
    assert score_result.total_points_before_clamp == 30

    dumped = score_result.model_dump()
    loaded = ScoreResult.model_validate(dumped)
    assert loaded == score_result


def test_investigation_findings_and_state_roundtrip() -> None:
    findings = InvestigationFindings(
        dns=DNSFinding(status=AgentStatus.OK),
        registration=RegistrationFinding(status=AgentStatus.OK),
        reputation=ReputationFinding(status=AgentStatus.OK),
    )
    assert findings.dns is not None
    assert findings.registration is not None
    assert findings.reputation is not None

    state = InvestigationState(
        domain="Example.COM",
        normalized_domain="example.com",
        findings=findings,
    )
    assert state.domain == "Example.COM"
    assert state.normalized_domain == "example.com"
    assert state.score is None

    dumped = state.model_dump()
    loaded = InvestigationState.model_validate(dumped)
    assert loaded == state
