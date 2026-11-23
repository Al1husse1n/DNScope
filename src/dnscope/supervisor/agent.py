from dnscope.schemas.common import AgentStatus
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.investigation import InvestigationFindings
from dnscope.schemas.supervisor import InconclusiveCheck, SupervisorAssessment
from dnscope.scoring.engine import score_findings
from dnscope.supervisor.explainer import Explainer, NullExplainer


class SupervisorAgent:
    def __init__(
        self,
        explainer: Explainer | None = None,  # None -> NullExplainer
    ) -> None:
        self._explainer: Explainer = explainer if explainer is not None else NullExplainer()

    async def assess(
        self,
        domain: str,
        dns: DNSFinding | None,
        registration: RegistrationFinding | None,
        reputation: ReputationFinding | None,
    ) -> SupervisorAssessment:
        """Produce a SupervisorAssessment.

        Steps (order is REQUIRED):
          1. Build InvestigationFindings from the three inputs.
          2. Call score_findings(...) from dnscope.scoring.engine.
             This is the ONLY place the score is computed.
          3. Build rule_trace_explanation from ScoreResult.rule_hits:
             a deterministic, human-readable string. No LLM.
             Format: one line per rule hit, e.g.
               "- DOMAIN_AGE_UNDER_7D (+30): Domain registered 3 days ago"
             If rule_hits is empty, use the line "No scoring rules triggered."
          4. Collect inconclusive_checks:
             - For each of dns/registration/reputation that is None, add an
               InconclusiveCheck(agent_name=..., reason="agent returned no finding")
             - For each finding whose status in (ERROR, SKIPPED), add
               InconclusiveCheck(agent_name=f.agent_name, reason=<joined errors or status>)
          5. If explainer is not None (or default NullExplainer), call
             await explainer.explain(domain, dns, registration, reputation, score_result).
             Wrap in try/except Exception; on exception, set narrative to
             f"Narrative generation failed: {type(exc).__name__}".
          6. Return SupervisorAssessment(
               score_result=score_result,   # UNCHANGED, byte-identical
               rule_trace_explanation=...,
               narrative=...,
               inconclusive_checks=...,
             )

        Never raises. Never mutates score_result.
        """
        # Step 1: Build InvestigationFindings
        findings = InvestigationFindings(
            dns=dns,
            registration=registration,
            reputation=reputation,
        )

        # Step 2: Deterministic score calculation
        score_result, _ = score_findings(findings)

        # Step 3: Build rule_trace_explanation
        if not score_result.rule_hits:
            rule_trace_explanation = "No scoring rules triggered."
        else:
            lines = [
                f"- {hit.rule_id} ({'+' if hit.points > 0 else ''}{hit.points}): {hit.description}"
                for hit in score_result.rule_hits
            ]
            rule_trace_explanation = "\n".join(lines)

        # Step 4: Collect inconclusive_checks
        inconclusive_checks: list[InconclusiveCheck] = []
        checks = [
            ("dns", dns),
            ("registration", registration),
            ("reputation", reputation),
        ]
        for name, finding in checks:
            if finding is None:
                inconclusive_checks.append(
                    InconclusiveCheck(agent_name=name, reason="agent returned no finding")
                )
            elif finding.status in (AgentStatus.ERROR, AgentStatus.SKIPPED):
                reason = "; ".join(finding.errors) if finding.errors else str(finding.status.value)
                inconclusive_checks.append(
                    InconclusiveCheck(agent_name=finding.agent_name, reason=reason)
                )

        # Step 5: Explainer call
        try:
            narrative_val = await self._explainer.explain(
                domain, dns, registration, reputation, score_result
            )
            narrative: str | None = str(narrative_val) if narrative_val is not None else None
        except Exception as exc:
            narrative = f"Narrative generation failed: {type(exc).__name__}"

        # Step 6: Return structured assessment
        return SupervisorAssessment(
            score_result=score_result,
            rule_trace_explanation=rule_trace_explanation,
            narrative=narrative,
            inconclusive_checks=inconclusive_checks,
        )
