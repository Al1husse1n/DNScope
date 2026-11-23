"""Scoring engine for aggregating agent findings into risk scores and rule traces."""

from dnscope.schemas.common import Evidence, RiskLevel
from dnscope.schemas.investigation import InvestigationFindings
from dnscope.schemas.scoring import RuleHit, ScoreResult
from dnscope.scoring.rules import (
    RULE_METADATA,
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


def _compute_risk_level(score: int) -> RiskLevel:
    """Map clamped score to RiskLevel: 0-24 LOW, 25-49 MEDIUM, 50-74 HIGH, 75-100 CRITICAL."""
    if score <= 24:
        return RiskLevel.LOW
    elif score <= 49:
        return RiskLevel.MEDIUM
    elif score <= 74:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def score_findings(
    findings: InvestigationFindings | None,
) -> tuple[ScoreResult, list[Evidence]]:
    """Score investigation findings deterministically and produce rule hits + evidence trace.

    Behavior:
    1. Run every rule against the corresponding finding.
    2. Sum points. Clamp final score to [0, 100].
    3. Map score -> RiskLevel: 0-24 LOW, 25-49 MEDIUM, 50-74 HIGH, 75-100 CRITICAL.
    4. Preserve total_points_before_clamp on ScoreResult for transparency.
    5. Return aggregated Evidence list (one per triggered rule, category as in the table).
    6. Never raise on missing findings.
    7. Deterministic: two calls with identical InvestigationFindings return identical ScoreResult.
       ScoreResult contains no timestamps.
    """
    if findings is None:
        findings = InvestigationFindings()

    rule_hits: list[RuleHit] = []

    # 1. Registration rules (evaluated in fixed table order)
    rule_hits.extend(check_domain_age_under_7d(findings.registration))
    rule_hits.extend(check_domain_age_under_30d(findings.registration))
    rule_hits.extend(check_domain_age_over_2y(findings.registration))

    # 2. DNS rules (evaluated in fixed table order)
    rule_hits.extend(check_no_a_records(findings.dns))
    rule_hits.extend(check_no_mx_records(findings.dns))
    rule_hits.extend(check_no_ns_records(findings.dns))
    rule_hits.extend(check_no_spf_record(findings.dns))

    # 3. Reputation rules (evaluated in fixed table order)
    rule_hits.extend(check_vt_malicious_high(findings.reputation))
    rule_hits.extend(check_vt_malicious_low(findings.reputation))
    rule_hits.extend(check_vt_suspicious(findings.reputation))
    rule_hits.extend(check_vt_clean(findings.reputation))
    rule_hits.extend(check_vt_unavailable(findings.reputation))

    # Compute raw points and clamped score
    total_points_before_clamp = sum(hit.points for hit in rule_hits)
    score = max(0, min(100, total_points_before_clamp))
    risk_level = _compute_risk_level(score)

    score_result = ScoreResult(
        score=score,
        risk_level=risk_level,
        rule_hits=rule_hits,
        total_points_before_clamp=total_points_before_clamp,
    )

    # Build Evidence list per triggered RuleHit
    evidence_list: list[Evidence] = []
    for hit in rule_hits:
        meta = RULE_METADATA.get(hit.rule_id)
        if meta is not None:
            evidence_list.append(
                Evidence(
                    category=meta.category,
                    label=hit.evidence_refs[0] if hit.evidence_refs else meta.evidence_label,
                    detail=hit.description,
                    source=meta.source,
                )
            )

    return score_result, evidence_list
