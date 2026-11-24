from typing import Any

from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import ScoreResult


def build_system_instruction() -> str:
    """Return the static system prompt for the Gemini explanation model.

    Instructs the model to:
      - Explain the provided deterministic score, never compute a new one.
      - Reference specific rule_ids from the ScoreResult when justifying.
      - Distinguish strong evidence (VT malicious detections) from weak
        (missing MX on a non-mail domain).
      - Explicitly state when a check was inconclusive or unavailable.
      - Return JSON matching the response schema.
      - Write 3–6 sentences, neutral analyst tone, no alarmism.
      - Never invent evidence not present in the findings.
    """
    return (
        "You are an expert cybersecurity analyst providing a concise threat narrative for a domain investigation.\n\n"
        "Instructions:\n"
        "1. Explain the provided deterministic score and risk assessment; never compute or propose a new score.\n"
        "2. Reference specific rule_ids from the ScoreResult when justifying findings.\n"
        "3. Distinguish strong evidence (e.g. VirusTotal malicious detections) from weak or contextual indicators "
        "(e.g. missing MX records on a non-mail domain).\n"
        "4. Explicitly state when an investigation check was inconclusive or unavailable.\n"
        "5. Write 3 to 6 sentences in a neutral, factual analyst tone without alarmism.\n"
        "6. Never invent, extrapolate, or hallucinate evidence not present in the provided findings.\n"
        "7. Return valid JSON matching the requested response schema with a single 'narrative' property."
    )


def build_user_message(
    domain: str,
    dns: DNSFinding | None,
    registration: RegistrationFinding | None,
    reputation: ReputationFinding | None,
    score_result: ScoreResult,
) -> str:
    """Return a compact, deterministic user message containing investigation findings.

    Contains:
      - The domain.
      - The ScoreResult (score, risk_level, rule_hits as bullet list).
      - A per-agent findings summary: for each of dns/registration/reputation,
        either 'unavailable' if None or a compact bullet list of non-empty fields.

    Omission guarantees:
      - Must NOT include Evidence timestamps (nondeterministic -> flaky).
      - Must NOT include the raw HTTPS response from VT — only extracted values.
      - If any finding agent is None, its section is marked as 'unavailable'.
    """
    lines: list[str] = [
        f"Domain: {domain}",
        "",
        "Deterministic Assessment:",
        f"- Score: {score_result.score}/100",
        f"- Risk Level: {score_result.risk_level.value}",
        "- Triggered Rules:",
    ]

    if score_result.rule_hits:
        for hit in score_result.rule_hits:
            lines.append(f"  * {hit.rule_id} ({hit.points:+d} pts): {hit.description}")
    else:
        lines.append("  * none (no rules triggered)")

    lines.append("")
    lines.append("Agent Findings:")

    # DNS Findings
    if dns is None:
        lines.append("- DNS Findings: unavailable")
    else:
        lines.append(f"- DNS Findings (status: {dns.status.value}):")
        if dns.a_records:
            lines.append(f"  * A records: {', '.join(sorted(dns.a_records))}")
        if dns.aaaa_records:
            lines.append(f"  * AAAA records: {', '.join(sorted(dns.aaaa_records))}")
        if dns.mx_records:
            lines.append(f"  * MX records: {', '.join(sorted(dns.mx_records))}")
        if dns.txt_records:
            lines.append(f"  * TXT records: {', '.join(sorted(dns.txt_records))}")
        if dns.ns_records:
            lines.append(f"  * NS records: {', '.join(sorted(dns.ns_records))}")
        if dns.has_spf is not None:
            lines.append(f"  * has_spf: {dns.has_spf}")
        if dns.errors:
            lines.append(f"  * errors: {', '.join(dns.errors)}")

    # Registration Findings
    if registration is None:
        lines.append("- Registration Findings: unavailable")
    else:
        lines.append(f"- Registration Findings (status: {registration.status.value}):")
        if registration.registrar:
            lines.append(f"  * registrar: {registration.registrar}")
        if registration.age_days is not None:
            lines.append(f"  * age_days: {registration.age_days}")
        if registration.created_at:
            created_date = registration.created_at.split("T")[0]
            lines.append(f"  * created_date: {created_date}")
        if registration.expires_at:
            expires_date = registration.expires_at.split("T")[0]
            lines.append(f"  * expires_date: {expires_date}")
        if registration.errors:
            lines.append(f"  * errors: {', '.join(registration.errors)}")

    # Reputation Findings
    if reputation is None:
        lines.append("- Reputation Findings: unavailable")
    else:
        lines.append(f"- Reputation Findings (status: {reputation.status.value}):")
        if reputation.detections_malicious is not None:
            lines.append(f"  * malicious_detections: {reputation.detections_malicious}")
        if reputation.detections_suspicious is not None:
            lines.append(f"  * suspicious_detections: {reputation.detections_suspicious}")
        if reputation.total_engines is not None:
            lines.append(f"  * total_engines: {reputation.total_engines}")
        if reputation.categories:
            lines.append(f"  * categories: {', '.join(sorted(reputation.categories))}")
        if reputation.permalink:
            lines.append(f"  * permalink: {reputation.permalink}")
        if reputation.errors:
            lines.append(f"  * errors: {', '.join(reputation.errors)}")

    return "\n".join(lines)


def build_response_schema() -> dict[str, Any]:
    """Return the JSON schema for Gemini's structured output.

    The schema MUST have a single required property: 'narrative' (type: string).
    It MUST NOT contain any numeric score field.
    """
    return {
        "type": "object",
        "properties": {
            "narrative": {
                "type": "string",
                "description": (
                    "Neutral 3-6 sentence technical analysis explaining the "
                    "deterministic risk assessment and rule triggers."
                ),
            },
        },
        "required": ["narrative"],
    }
