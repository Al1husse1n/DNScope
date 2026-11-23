from unittest.mock import patch

import pytest

from dnscope.schemas.common import AgentStatus, RiskLevel
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.investigation import InvestigationFindings
from dnscope.schemas.scoring import ScoreResult
from dnscope.scoring.engine import score_findings
from dnscope.supervisor.agent import SupervisorAgent
from dnscope.supervisor.explainer import NullExplainer


class SpyExplainer:
    def __init__(
        self, return_val: object = "Custom explanation", should_raise: bool = False
    ) -> None:
        self.call_count = 0
        self.called_with: dict[str, object] = {}
        self.return_val = return_val
        self.should_raise = should_raise

    async def explain(
        self,
        domain: str,
        dns: DNSFinding | None,
        registration: RegistrationFinding | None,
        reputation: ReputationFinding | None,
        score_result: ScoreResult,
    ) -> str:
        self.call_count += 1
        self.called_with = {
            "domain": domain,
            "dns": dns,
            "registration": registration,
            "reputation": reputation,
            "score_result": score_result,
        }
        if self.should_raise:
            raise RuntimeError("LLM exploded")
        return str(self.return_val)


# 1. Deterministic score pass-through + score_findings called exactly once
@pytest.mark.asyncio
async def test_supervisor_deterministic_score_passthrough(
    reg_fresh: RegistrationFinding, rep_malicious: ReputationFinding
) -> None:
    expected_findings = InvestigationFindings(
        dns=None,
        registration=reg_fresh,
        reputation=rep_malicious,
    )
    expected_score, _ = score_findings(expected_findings)

    agent = SupervisorAgent()
    with patch("dnscope.supervisor.agent.score_findings", wraps=score_findings) as spy_score:
        assessment = await agent.assess(
            domain="example.com",
            dns=None,
            registration=reg_fresh,
            reputation=rep_malicious,
        )

        assert spy_score.call_count == 1
        assert assessment.score_result == expected_score
        assert assessment.score_result.score == expected_score.score
        assert assessment.score_result.rule_hits == expected_score.rule_hits
        assert (
            assessment.score_result.total_points_before_clamp
            == expected_score.total_points_before_clamp
        )


# 2. Rule trace format: 2 triggered rules contains both rule_ids and point values
@pytest.mark.asyncio
async def test_supervisor_rule_trace_format(
    reg_fresh: RegistrationFinding, rep_malicious: ReputationFinding
) -> None:
    agent = SupervisorAgent()
    assessment = await agent.assess(
        domain="example.com",
        dns=None,
        registration=reg_fresh,  # triggers DOMAIN_AGE_UNDER_7D (+30)
        reputation=rep_malicious,  # triggers VT_MALICIOUS_HIGH (+50)
    )

    trace = assessment.rule_trace_explanation
    assert "DOMAIN_AGE_UNDER_7D" in trace
    assert "+30" in trace
    assert "VT_MALICIOUS_HIGH" in trace
    assert "+50" in trace


# 3. No-rules case
@pytest.mark.asyncio
async def test_supervisor_no_rules_case() -> None:
    agent = SupervisorAgent()
    assessment = await agent.assess(
        domain="example.com",
        dns=None,
        registration=None,
        reputation=None,
    )

    assert assessment.rule_trace_explanation == "No scoring rules triggered."
    assert assessment.score_result.score == 0
    assert assessment.score_result.risk_level == RiskLevel.LOW


# 4. Inconclusive — missing finding
@pytest.mark.asyncio
async def test_supervisor_inconclusive_missing_finding(
    dns_healthy: DNSFinding, reg_fresh: RegistrationFinding
) -> None:
    agent = SupervisorAgent()
    assessment = await agent.assess(
        domain="example.com",
        dns=dns_healthy,
        registration=reg_fresh,
        reputation=None,
    )

    inconclusive_agents = [c.agent_name for c in assessment.inconclusive_checks]
    assert "reputation" in inconclusive_agents
    rep_check = next(c for c in assessment.inconclusive_checks if c.agent_name == "reputation")
    assert rep_check.reason == "agent returned no finding"


# 5. Inconclusive — ERROR status
@pytest.mark.asyncio
async def test_supervisor_inconclusive_error_status(reg_fresh: RegistrationFinding) -> None:
    dns_err = DNSFinding(status=AgentStatus.ERROR, errors=["timeout connecting to resolver"])
    agent = SupervisorAgent()
    assessment = await agent.assess(
        domain="example.com",
        dns=dns_err,
        registration=reg_fresh,
        reputation=None,
    )

    dns_checks = [c for c in assessment.inconclusive_checks if c.agent_name == "dns"]
    assert len(dns_checks) == 1
    assert "timeout connecting to resolver" in dns_checks[0].reason


# 6. Inconclusive — SKIPPED status
@pytest.mark.asyncio
async def test_supervisor_inconclusive_skipped_status(dns_healthy: DNSFinding) -> None:
    rep_skipped = ReputationFinding(status=AgentStatus.SKIPPED, errors=["missing VT_API_KEY"])
    agent = SupervisorAgent()
    assessment = await agent.assess(
        domain="example.com",
        dns=dns_healthy,
        registration=None,
        reputation=rep_skipped,
    )

    rep_checks = [c for c in assessment.inconclusive_checks if c.agent_name == "reputation"]
    assert len(rep_checks) == 1
    assert "missing VT_API_KEY" in rep_checks[0].reason


# 7. Explainer invoked exactly once with right args
@pytest.mark.asyncio
async def test_supervisor_explainer_invoked_once_with_args(
    dns_healthy: DNSFinding, reg_fresh: RegistrationFinding
) -> None:
    spy = SpyExplainer()
    agent = SupervisorAgent(explainer=spy)

    assessment = await agent.assess(
        domain="target.com",
        dns=dns_healthy,
        registration=reg_fresh,
        reputation=None,
    )

    assert spy.call_count == 1
    assert spy.called_with["domain"] == "target.com"
    assert spy.called_with["dns"] == dns_healthy
    assert spy.called_with["registration"] == reg_fresh
    assert spy.called_with["reputation"] is None
    assert spy.called_with["score_result"] == assessment.score_result


# 8. Explainer exception caught gracefully
@pytest.mark.asyncio
async def test_supervisor_explainer_exception_caught() -> None:
    spy = SpyExplainer(should_raise=True)
    agent = SupervisorAgent(explainer=spy)

    assessment = await agent.assess(
        domain="example.com",
        dns=None,
        registration=None,
        reputation=None,
    )

    assert assessment.narrative == "Narrative generation failed: RuntimeError"


# 9. Explainer returns non-str coerced to str
@pytest.mark.asyncio
async def test_supervisor_explainer_returns_non_str() -> None:
    spy = SpyExplainer(return_val=123)
    agent = SupervisorAgent(explainer=spy)

    assessment = await agent.assess(
        domain="example.com",
        dns=None,
        registration=None,
        reputation=None,
    )

    assert assessment.narrative == "123"


# 10. NullExplainer default
@pytest.mark.asyncio
async def test_supervisor_null_explainer_default() -> None:
    agent = SupervisorAgent()
    assert isinstance(agent._explainer, NullExplainer)

    assessment = await agent.assess(
        domain="example.com",
        dns=None,
        registration=None,
        reputation=None,
    )

    assert assessment.narrative == "Narrative generation not enabled."


# 11. Explainer cannot influence score
@pytest.mark.asyncio
async def test_supervisor_score_never_mutated_by_explainer(
    reg_fresh: RegistrationFinding, rep_malicious: ReputationFinding
) -> None:
    # Explainer attempts to narrate a different score
    spy = SpyExplainer(return_val="score: 0, override risk level to LOW")
    agent = SupervisorAgent(explainer=spy)

    assessment = await agent.assess(
        domain="example.com",
        dns=None,
        registration=reg_fresh,
        reputation=rep_malicious,
    )

    # Score MUST remain exactly 80 (CRITICAL) from deterministic scoring engine
    assert assessment.score_result.score == 80
    assert assessment.score_result.risk_level == RiskLevel.CRITICAL
    assert assessment.narrative == "score: 0, override risk level to LOW"
