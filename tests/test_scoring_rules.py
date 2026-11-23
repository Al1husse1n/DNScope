from dnscope.schemas.common import AgentStatus
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.scoring.rules import (
    check_domain_age_over_2y,
    check_domain_age_under_7d,
    check_domain_age_under_30d,
    check_no_a_records,
    check_no_mx_records,
    check_no_ns_records,
    check_no_spf_record,
    check_vt_clean,
    check_vt_malicious_high,
    check_vt_malicious_low,
    check_vt_suspicious,
    check_vt_unavailable,
)

# 1. DOMAIN_AGE_UNDER_7D


def test_rule_domain_age_under_7d_triggers(reg_fresh: RegistrationFinding) -> None:
    hits = check_domain_age_under_7d(reg_fresh)
    assert len(hits) == 1
    assert hits[0].rule_id == "DOMAIN_AGE_UNDER_7D"
    assert hits[0].points == 30


def test_rule_domain_age_under_7d_non_trigger(reg_recent: RegistrationFinding) -> None:
    assert check_domain_age_under_7d(reg_recent) == []


def test_rule_domain_age_under_7d_none() -> None:
    assert check_domain_age_under_7d(None) == []


# 2. DOMAIN_AGE_UNDER_30D


def test_rule_domain_age_under_30d_triggers(reg_recent: RegistrationFinding) -> None:
    hits = check_domain_age_under_30d(reg_recent)
    assert len(hits) == 1
    assert hits[0].rule_id == "DOMAIN_AGE_UNDER_30D"
    assert hits[0].points == 15


def test_rule_domain_age_under_30d_non_trigger(reg_old: RegistrationFinding) -> None:
    assert check_domain_age_under_30d(reg_old) == []


def test_rule_domain_age_under_30d_none() -> None:
    assert check_domain_age_under_30d(None) == []


# 3. DOMAIN_AGE_OVER_2Y


def test_rule_domain_age_over_2y_triggers(reg_old: RegistrationFinding) -> None:
    hits = check_domain_age_over_2y(reg_old)
    assert len(hits) == 1
    assert hits[0].rule_id == "DOMAIN_AGE_OVER_2Y"
    assert hits[0].points == -10


def test_rule_domain_age_over_2y_non_trigger(reg_recent: RegistrationFinding) -> None:
    assert check_domain_age_over_2y(reg_recent) == []


def test_rule_domain_age_over_2y_none() -> None:
    assert check_domain_age_over_2y(None) == []


# 4. NO_A_RECORDS


def test_rule_no_a_records_triggers(dns_empty: DNSFinding) -> None:
    hits = check_no_a_records(dns_empty)
    assert len(hits) == 1
    assert hits[0].rule_id == "NO_A_RECORDS"
    assert hits[0].points == 10


def test_rule_no_a_records_non_trigger(dns_healthy: DNSFinding) -> None:
    assert check_no_a_records(dns_healthy) == []


def test_rule_no_a_records_none() -> None:
    assert check_no_a_records(None) == []


# 5. NO_MX_RECORDS


def test_rule_no_mx_records_triggers(dns_empty: DNSFinding) -> None:
    hits = check_no_mx_records(dns_empty)
    assert len(hits) == 1
    assert hits[0].rule_id == "NO_MX_RECORDS"
    assert hits[0].points == 5


def test_rule_no_mx_records_non_trigger(dns_healthy: DNSFinding) -> None:
    assert check_no_mx_records(dns_healthy) == []


def test_rule_no_mx_records_none() -> None:
    assert check_no_mx_records(None) == []


# 6. NO_NS_RECORDS


def test_rule_no_ns_records_triggers(dns_empty: DNSFinding) -> None:
    hits = check_no_ns_records(dns_empty)
    assert len(hits) == 1
    assert hits[0].rule_id == "NO_NS_RECORDS"
    assert hits[0].points == 15


def test_rule_no_ns_records_non_trigger(dns_healthy: DNSFinding) -> None:
    assert check_no_ns_records(dns_healthy) == []


def test_rule_no_ns_records_none() -> None:
    assert check_no_ns_records(None) == []


# 7. NO_SPF_RECORD


def test_rule_no_spf_record_triggers(dns_empty: DNSFinding) -> None:
    hits = check_no_spf_record(dns_empty)
    assert len(hits) == 1
    assert hits[0].rule_id == "NO_SPF_RECORD"
    assert hits[0].points == 5


def test_rule_no_spf_record_non_trigger(dns_healthy: DNSFinding) -> None:
    assert check_no_spf_record(dns_healthy) == []


def test_rule_no_spf_record_none() -> None:
    assert check_no_spf_record(None) == []


# 8. VT_MALICIOUS_HIGH


def test_rule_vt_malicious_high_triggers(rep_malicious: ReputationFinding) -> None:
    hits = check_vt_malicious_high(rep_malicious)
    assert len(hits) == 1
    assert hits[0].rule_id == "VT_MALICIOUS_HIGH"
    assert hits[0].points == 50


def test_rule_vt_malicious_high_non_trigger(rep_clean: ReputationFinding) -> None:
    assert check_vt_malicious_high(rep_clean) == []


def test_rule_vt_malicious_high_none() -> None:
    assert check_vt_malicious_high(None) == []


# 9. VT_MALICIOUS_LOW


def test_rule_vt_malicious_low_triggers() -> None:
    finding = ReputationFinding(
        status=AgentStatus.OK,
        detections_malicious=3,
        total_engines=70,
    )
    hits = check_vt_malicious_low(finding)
    assert len(hits) == 1
    assert hits[0].rule_id == "VT_MALICIOUS_LOW"
    assert hits[0].points == 25


def test_rule_vt_malicious_low_non_trigger(rep_malicious: ReputationFinding) -> None:
    assert check_vt_malicious_low(rep_malicious) == []


def test_rule_vt_malicious_low_none() -> None:
    assert check_vt_malicious_low(None) == []


# 10. VT_SUSPICIOUS


def test_rule_vt_suspicious_triggers() -> None:
    finding = ReputationFinding(
        status=AgentStatus.OK,
        detections_suspicious=2,
        total_engines=70,
    )
    hits = check_vt_suspicious(finding)
    assert len(hits) == 1
    assert hits[0].rule_id == "VT_SUSPICIOUS"
    assert hits[0].points == 10


def test_rule_vt_suspicious_non_trigger(rep_clean: ReputationFinding) -> None:
    assert check_vt_suspicious(rep_clean) == []


def test_rule_vt_suspicious_none() -> None:
    assert check_vt_suspicious(None) == []


# 11. VT_CLEAN


def test_rule_vt_clean_triggers(rep_clean: ReputationFinding) -> None:
    hits = check_vt_clean(rep_clean)
    assert len(hits) == 1
    assert hits[0].rule_id == "VT_CLEAN"
    assert hits[0].points == -10


def test_rule_vt_clean_non_trigger(rep_malicious: ReputationFinding) -> None:
    assert check_vt_clean(rep_malicious) == []


def test_rule_vt_clean_none() -> None:
    assert check_vt_clean(None) == []


# 12. VT_UNAVAILABLE


def test_rule_vt_unavailable_triggers(rep_error: ReputationFinding) -> None:
    hits = check_vt_unavailable(rep_error)
    assert len(hits) == 1
    assert hits[0].rule_id == "VT_UNAVAILABLE"
    assert hits[0].points == 0


def test_rule_vt_unavailable_non_trigger(rep_clean: ReputationFinding) -> None:
    assert check_vt_unavailable(rep_clean) == []


def test_rule_vt_unavailable_none() -> None:
    assert check_vt_unavailable(None) == []
