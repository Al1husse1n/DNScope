import re

from dnscope.schemas.common import AgentStatus, Evidence, EvidenceCategory, RiskLevel
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import RuleHit, ScoreResult
from dnscope.supervisor.prompts import (
    build_response_schema,
    build_system_instruction,
    build_user_message,
)


def test_system_instruction_content() -> None:
    system_prompt = build_system_instruction()
    lower = system_prompt.lower()
    assert "deterministic" in lower
    assert "rule_ids" in lower
    assert "json" in lower


def test_system_instruction_is_deterministic() -> None:
    p1 = build_system_instruction()
    p2 = build_system_instruction()
    assert p1 == p2


def test_user_message_contains_score() -> None:
    score_result = ScoreResult(
        score=80,
        risk_level=RiskLevel.CRITICAL,
        rule_hits=[],
        total_points_before_clamp=80,
    )
    msg = build_user_message("example.com", None, None, None, score_result)
    assert "80" in msg
    assert "CRITICAL" in msg


def test_user_message_contains_all_triggered_rule_ids() -> None:
    hits = [
        RuleHit(
            rule_id="DOMAIN_AGE_UNDER_7D",
            description="Domain was registered less than 7 days ago",
            points=30,
            evidence_refs=["age"],
        ),
        RuleHit(
            rule_id="VT_MALICIOUS_DETECTIONS_HIGH",
            description="5 or more security vendors flagged domain as malicious",
            points=40,
            evidence_refs=["vt"],
        ),
    ]
    score_result = ScoreResult(
        score=70,
        risk_level=RiskLevel.HIGH,
        rule_hits=hits,
        total_points_before_clamp=70,
    )
    msg = build_user_message("example.com", None, None, None, score_result)
    assert "DOMAIN_AGE_UNDER_7D" in msg
    assert "VT_MALICIOUS_DETECTIONS_HIGH" in msg


def test_user_message_with_missing_findings() -> None:
    score_result = ScoreResult(
        score=0,
        risk_level=RiskLevel.LOW,
        rule_hits=[],
        total_points_before_clamp=0,
    )
    msg = build_user_message("example.com", None, None, None, score_result)
    assert "unavailable" in msg
    assert "- DNS Findings: unavailable" in msg
    assert "- Registration Findings: unavailable" in msg
    assert "- Reputation Findings: unavailable" in msg


def test_user_message_is_deterministic() -> None:
    dns = DNSFinding(status=AgentStatus.OK, a_records=["1.1.1.1"], mx_records=["mail.com"])
    reg = RegistrationFinding(status=AgentStatus.OK, registrar="GoDaddy", age_days=10)
    rep = ReputationFinding(status=AgentStatus.OK, detections_malicious=0, total_engines=90)
    score = ScoreResult(
        score=10, risk_level=RiskLevel.LOW, rule_hits=[], total_points_before_clamp=10
    )

    m1 = build_user_message("example.com", dns, reg, rep, score)
    m2 = build_user_message("example.com", dns, reg, rep, score)
    assert m1 == m2


def test_user_message_does_not_contain_evidence_timestamps() -> None:
    evidence = Evidence(
        category=EvidenceCategory.MALICIOUS,
        label="suspicious_record",
        detail="suspicious detail",
        source="dns",
    )
    dns = DNSFinding(status=AgentStatus.OK, evidence=[evidence], a_records=["1.2.3.4"])
    reg = RegistrationFinding(
        status=AgentStatus.OK,
        created_at="2024-01-01T12:00:00Z",
        expires_at="2025-01-01T12:00:00Z",
        evidence=[evidence],
    )
    rep = ReputationFinding(status=AgentStatus.OK, evidence=[evidence])
    score = ScoreResult(
        score=50, risk_level=RiskLevel.MEDIUM, rule_hits=[], total_points_before_clamp=50
    )

    msg = build_user_message("example.com", dns, reg, rep, score)
    # Check that no ISO datetime substring matching \d{4}-\d{2}-\d{2}T appears in the message
    match = re.search(r"\d{4}-\d{2}-\d{2}T", msg)
    assert match is None, f"Found ISO timestamp in message: {match.group(0)}"


def test_response_schema_has_single_required_narrative_and_no_score() -> None:
    schema = build_response_schema()
    assert schema.get("type") == "object"
    assert "properties" in schema
    assert list(schema["properties"].keys()) == ["narrative"]
    assert schema.get("required") == ["narrative"]

    # Recursive check that 'score' does not appear anywhere in schema keys or string values
    def recursive_find_score(node: object) -> bool:
        if isinstance(node, dict):
            for k, v in node.items():
                if "score" in str(k).lower():
                    return True
                if recursive_find_score(v):
                    return True
        elif isinstance(node, list):
            for item in node:
                if recursive_find_score(item):
                    return True
        elif isinstance(node, str) and "score" in node.lower():
            return True
        return False

    assert not recursive_find_score(schema), "Found 'score' in response schema"


def test_response_schema_is_deterministic() -> None:
    s1 = build_response_schema()
    s2 = build_response_schema()
    assert s1 == s2
