"""Scoring rules for domain investigation findings.

Evidence vs RuleHit Contract Split:
Each rule function in this module is a pure function returning a `list[RuleHit]`.
Empty list indicates the rule did not trigger. Rules must never raise on None inputs —
missing findings or missing fields are treated as "rule does not apply".
Rules emit `RuleHit` with a human-readable description and `evidence_refs` listing the
evidence label(s) that triggered it.

The scoring engine (`dnscope.scoring.engine`) is responsible for constructing `Evidence`
objects per triggered `RuleHit` using the rule's declared category and source metadata
(defined in `RULE_METADATA`). This separation guarantees that score computation remains
pure and deterministic while keeping evidence records and score traces synchronized.
"""

from typing import NamedTuple

from dnscope.schemas.common import AgentStatus, EvidenceCategory
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import RuleHit


class RuleMeta(NamedTuple):
    category: EvidenceCategory
    source: str
    points: int
    evidence_label: str


RULE_METADATA: dict[str, RuleMeta] = {
    "DOMAIN_AGE_UNDER_7D": RuleMeta(
        category=EvidenceCategory.SUSPICIOUS,
        source="rdap",
        points=30,
        evidence_label="domain_age_under_7d",
    ),
    "DOMAIN_AGE_UNDER_30D": RuleMeta(
        category=EvidenceCategory.SUSPICIOUS,
        source="rdap",
        points=15,
        evidence_label="domain_age_under_30d",
    ),
    "DOMAIN_AGE_OVER_2Y": RuleMeta(
        category=EvidenceCategory.BENIGN,
        source="rdap",
        points=-10,
        evidence_label="domain_age_over_2y",
    ),
    "NO_A_RECORDS": RuleMeta(
        category=EvidenceCategory.SUSPICIOUS,
        source="dns",
        points=10,
        evidence_label="no_a_records",
    ),
    "NO_MX_RECORDS": RuleMeta(
        category=EvidenceCategory.INCONCLUSIVE,
        source="dns",
        points=5,
        evidence_label="no_mx_records",
    ),
    "NO_NS_RECORDS": RuleMeta(
        category=EvidenceCategory.SUSPICIOUS,
        source="dns",
        points=15,
        evidence_label="no_ns_records",
    ),
    "NO_SPF_RECORD": RuleMeta(
        category=EvidenceCategory.INCONCLUSIVE,
        source="dns",
        points=5,
        evidence_label="no_spf_record",
    ),
    "VT_MALICIOUS_HIGH": RuleMeta(
        category=EvidenceCategory.MALICIOUS,
        source="virustotal",
        points=50,
        evidence_label="vt_malicious_high",
    ),
    "VT_MALICIOUS_LOW": RuleMeta(
        category=EvidenceCategory.MALICIOUS,
        source="virustotal",
        points=25,
        evidence_label="vt_malicious_low",
    ),
    "VT_SUSPICIOUS": RuleMeta(
        category=EvidenceCategory.SUSPICIOUS,
        source="virustotal",
        points=10,
        evidence_label="vt_suspicious",
    ),
    "VT_CLEAN": RuleMeta(
        category=EvidenceCategory.BENIGN,
        source="virustotal",
        points=-10,
        evidence_label="vt_clean",
    ),
    "VT_UNAVAILABLE": RuleMeta(
        category=EvidenceCategory.INCONCLUSIVE,
        source="virustotal",
        points=0,
        evidence_label="vt_unavailable",
    ),
}


# Registration Rules


def check_domain_age_under_7d(reg: RegistrationFinding | None) -> list[RuleHit]:
    """Trigger when reg.age_days is not None and reg.age_days < 7 (+30 points)."""
    if reg is not None and reg.age_days is not None and reg.age_days < 7:
        meta = RULE_METADATA["DOMAIN_AGE_UNDER_7D"]
        return [
            RuleHit(
                rule_id="DOMAIN_AGE_UNDER_7D",
                description="Domain is registered less than 7 days ago",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_domain_age_under_30d(reg: RegistrationFinding | None) -> list[RuleHit]:
    """Trigger when 7 <= reg.age_days < 30 (+15 points)."""
    if reg is not None and reg.age_days is not None and 7 <= reg.age_days < 30:
        meta = RULE_METADATA["DOMAIN_AGE_UNDER_30D"]
        return [
            RuleHit(
                rule_id="DOMAIN_AGE_UNDER_30D",
                description="Domain is registered between 7 and 30 days ago",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_domain_age_over_2y(reg: RegistrationFinding | None) -> list[RuleHit]:
    """Trigger when reg.age_days >= 730 (-10 points)."""
    if reg is not None and reg.age_days is not None and reg.age_days >= 730:
        meta = RULE_METADATA["DOMAIN_AGE_OVER_2Y"]
        return [
            RuleHit(
                rule_id="DOMAIN_AGE_OVER_2Y",
                description="Domain has been registered for over 2 years (>= 730 days)",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


# DNS Rules


def check_no_a_records(dns: DNSFinding | None) -> list[RuleHit]:
    """Trigger when dns.status == OK and not dns.a_records and not dns.aaaa_records (+10 points)."""
    if (
        dns is not None
        and dns.status == AgentStatus.OK
        and not dns.a_records
        and not dns.aaaa_records
    ):
        meta = RULE_METADATA["NO_A_RECORDS"]
        return [
            RuleHit(
                rule_id="NO_A_RECORDS",
                description="DNS check succeeded but no A or AAAA records found",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_no_mx_records(dns: DNSFinding | None) -> list[RuleHit]:
    """Trigger when dns.status == OK and not dns.mx_records (+5 points)."""
    if dns is not None and dns.status == AgentStatus.OK and not dns.mx_records:
        meta = RULE_METADATA["NO_MX_RECORDS"]
        return [
            RuleHit(
                rule_id="NO_MX_RECORDS",
                description="DNS check succeeded but no MX records found",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_no_ns_records(dns: DNSFinding | None) -> list[RuleHit]:
    """Trigger when dns.status == OK and not dns.ns_records (+15 points)."""
    if dns is not None and dns.status == AgentStatus.OK and not dns.ns_records:
        meta = RULE_METADATA["NO_NS_RECORDS"]
        return [
            RuleHit(
                rule_id="NO_NS_RECORDS",
                description="DNS check succeeded but no NS records found",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_no_spf_record(dns: DNSFinding | None) -> list[RuleHit]:
    """Trigger when dns.status == OK and dns.has_spf is False (+5 points)."""
    if dns is not None and dns.status == AgentStatus.OK and dns.has_spf is False:
        meta = RULE_METADATA["NO_SPF_RECORD"]
        return [
            RuleHit(
                rule_id="NO_SPF_RECORD",
                description="DNS check succeeded but no SPF record found (has_spf is False)",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


# VirusTotal / Reputation Rules


def check_vt_malicious_high(rep: ReputationFinding | None) -> list[RuleHit]:
    """Trigger when rep.detections_malicious is not None and rep.detections_malicious >= 5 (+50 points)."""
    if rep is not None and rep.detections_malicious is not None and rep.detections_malicious >= 5:
        meta = RULE_METADATA["VT_MALICIOUS_HIGH"]
        return [
            RuleHit(
                rule_id="VT_MALICIOUS_HIGH",
                description="VirusTotal reports 5 or more malicious engine detections",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_vt_malicious_low(rep: ReputationFinding | None) -> list[RuleHit]:
    """Trigger when 1 <= rep.detections_malicious < 5 (+25 points)."""
    if (
        rep is not None
        and rep.detections_malicious is not None
        and 1 <= rep.detections_malicious < 5
    ):
        meta = RULE_METADATA["VT_MALICIOUS_LOW"]
        return [
            RuleHit(
                rule_id="VT_MALICIOUS_LOW",
                description="VirusTotal reports between 1 and 4 malicious engine detections",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_vt_suspicious(rep: ReputationFinding | None) -> list[RuleHit]:
    """Trigger when rep.detections_suspicious is not None and rep.detections_suspicious >= 1 (+10 points)."""
    if rep is not None and rep.detections_suspicious is not None and rep.detections_suspicious >= 1:
        meta = RULE_METADATA["VT_SUSPICIOUS"]
        return [
            RuleHit(
                rule_id="VT_SUSPICIOUS",
                description="VirusTotal reports 1 or more suspicious engine detections",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_vt_clean(rep: ReputationFinding | None) -> list[RuleHit]:
    """Trigger when rep.total_engines and rep.detections_malicious == 0 (-10 points)."""
    if rep is not None and bool(rep.total_engines) and rep.detections_malicious == 0:
        meta = RULE_METADATA["VT_CLEAN"]
        return [
            RuleHit(
                rule_id="VT_CLEAN",
                description="VirusTotal scanned engines with 0 malicious detections",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


def check_vt_unavailable(rep: ReputationFinding | None) -> list[RuleHit]:
    """Trigger when rep.status in (AgentStatus.ERROR, AgentStatus.SKIPPED) (0 points)."""
    if rep is not None and rep.status in (AgentStatus.ERROR, AgentStatus.SKIPPED):
        meta = RULE_METADATA["VT_UNAVAILABLE"]
        return [
            RuleHit(
                rule_id="VT_UNAVAILABLE",
                description="VirusTotal reputation check was unavailable (agent error or skipped)",
                points=meta.points,
                evidence_refs=[meta.evidence_label],
            )
        ]
    return []


# Aliases for rule_* naming convention
rule_domain_age_under_7d = check_domain_age_under_7d
rule_domain_age_under_30d = check_domain_age_under_30d
rule_domain_age_over_2y = check_domain_age_over_2y
rule_no_a_records = check_no_a_records
rule_no_mx_records = check_no_mx_records
rule_no_ns_records = check_no_ns_records
rule_no_spf_record = check_no_spf_record
rule_vt_malicious_high = check_vt_malicious_high
rule_vt_malicious_low = check_vt_malicious_low
rule_vt_suspicious = check_vt_suspicious
rule_vt_clean = check_vt_clean
rule_vt_unavailable = check_vt_unavailable
