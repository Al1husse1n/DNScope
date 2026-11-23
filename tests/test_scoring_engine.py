from dnscope.schemas.common import AgentStatus, EvidenceCategory, RiskLevel
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.investigation import InvestigationFindings
from dnscope.scoring.engine import score_findings


def test_fresh_domain_vt_malicious_critical(
    reg_fresh: RegistrationFinding, rep_malicious: ReputationFinding
) -> None:
    findings = InvestigationFindings(
        registration=reg_fresh,
        reputation=rep_malicious,
    )
    score_result, evidence = score_findings(findings)
    assert score_result.score >= 75
    assert score_result.risk_level == RiskLevel.CRITICAL
    rule_ids = [hit.rule_id for hit in score_result.rule_hits]
    assert "DOMAIN_AGE_UNDER_7D" in rule_ids
    assert "VT_MALICIOUS_HIGH" in rule_ids
    assert len(evidence) == len(score_result.rule_hits)


def test_old_domain_vt_clean_low(
    reg_old: RegistrationFinding, rep_clean: ReputationFinding, dns_healthy: DNSFinding
) -> None:
    findings = InvestigationFindings(
        registration=reg_old,
        reputation=rep_clean,
        dns=dns_healthy,
    )
    score_result, evidence = score_findings(findings)
    assert score_result.risk_level == RiskLevel.LOW
    assert score_result.score <= 25
    rule_ids = [hit.rule_id for hit in score_result.rule_hits]
    assert "DOMAIN_AGE_OVER_2Y" in rule_ids
    assert "VT_CLEAN" in rule_ids
    assert len(evidence) == len(score_result.rule_hits)


def test_all_findings_none_returns_zero_low() -> None:
    findings = InvestigationFindings()
    score_result, evidence = score_findings(findings)
    assert score_result.score == 0
    assert score_result.risk_level == RiskLevel.LOW
    assert score_result.rule_hits == []
    assert score_result.total_points_before_clamp == 0
    assert evidence == []

    # Also test passing None directly
    score_result_none, evidence_none = score_findings(None)
    assert score_result_none.score == 0
    assert score_result_none.risk_level == RiskLevel.LOW
    assert score_result_none.rule_hits == []
    assert score_result_none.total_points_before_clamp == 0
    assert evidence_none == []


def test_all_agents_error_returns_low_and_inconclusive_evidence(
    dns_error: DNSFinding, rep_error: ReputationFinding
) -> None:
    reg_error = RegistrationFinding(
        agent_name="registration",
        status=AgentStatus.ERROR,
        errors=["RDAP connection refused"],
    )
    findings = InvestigationFindings(
        dns=dns_error,
        registration=reg_error,
        reputation=rep_error,
    )
    score_result, evidence = score_findings(findings)
    assert score_result.risk_level == RiskLevel.LOW
    assert score_result.score == 0

    # VT_UNAVAILABLE triggers and provides an INCONCLUSIVE evidence entry
    rule_ids = [hit.rule_id for hit in score_result.rule_hits]
    assert "VT_UNAVAILABLE" in rule_ids
    inconclusive_evidences = [ev for ev in evidence if ev.category == EvidenceCategory.INCONCLUSIVE]
    assert len(inconclusive_evidences) >= 1
    assert any(ev.label == "vt_unavailable" for ev in inconclusive_evidences)


def test_determinism_identical_findings_identical_score_result(
    reg_fresh: RegistrationFinding,
    rep_malicious: ReputationFinding,
    dns_empty: DNSFinding,
) -> None:
    findings = InvestigationFindings(
        registration=reg_fresh,
        reputation=rep_malicious,
        dns=dns_empty,
    )
    result_1, _ = score_findings(findings)
    result_2, _ = score_findings(findings)

    assert result_1 == result_2
    assert result_1.model_dump() == result_2.model_dump()


def test_clamp_exceeds_100_points() -> None:
    # Synthetic scenario:
    # DOMAIN_AGE_UNDER_7D (+30)
    # NO_A_RECORDS (+10)
    # NO_MX_RECORDS (+5)
    # NO_NS_RECORDS (+15)
    # NO_SPF_RECORD (+5)
    # VT_MALICIOUS_HIGH (+50)
    # VT_SUSPICIOUS (+10)
    # Total = 30 + 10 + 5 + 15 + 5 + 50 + 10 = 125 > 100
    dns = DNSFinding(
        status=AgentStatus.OK,
        a_records=[],
        aaaa_records=[],
        mx_records=[],
        ns_records=[],
        has_spf=False,
    )
    reg = RegistrationFinding(
        status=AgentStatus.OK,
        age_days=1,
    )
    rep = ReputationFinding(
        status=AgentStatus.OK,
        detections_malicious=10,
        detections_suspicious=3,
        total_engines=70,
    )
    findings = InvestigationFindings(dns=dns, registration=reg, reputation=rep)
    score_result, evidence = score_findings(findings)

    assert score_result.total_points_before_clamp > 100
    assert score_result.total_points_before_clamp == 125
    assert score_result.score == 100
    assert score_result.risk_level == RiskLevel.CRITICAL
    assert len(evidence) == len(score_result.rule_hits)


def test_clamp_below_zero_points() -> None:
    # Synthetic scenario:
    # DOMAIN_AGE_OVER_2Y (-10)
    # VT_CLEAN (-10)
    # Total = -20 < 0
    reg = RegistrationFinding(
        status=AgentStatus.OK,
        age_days=1000,
    )
    rep = ReputationFinding(
        status=AgentStatus.OK,
        detections_malicious=0,
        detections_suspicious=0,
        total_engines=70,
    )
    findings = InvestigationFindings(registration=reg, reputation=rep)
    score_result, evidence = score_findings(findings)

    assert score_result.total_points_before_clamp < 0
    assert score_result.total_points_before_clamp == -20
    assert score_result.score == 0
    assert score_result.risk_level == RiskLevel.LOW
    assert len(evidence) == len(score_result.rule_hits)
