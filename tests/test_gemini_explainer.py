import json
import os
from typing import Any

import pytest

from dnscope.config import Settings
from dnscope.schemas.common import AgentStatus, RiskLevel
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import RuleHit, ScoreResult
from dnscope.supervisor.agent import SupervisorAgent
from dnscope.supervisor.gemini_explainer import GeminiExplainer


class FakeResponse:
    def __init__(
        self,
        text: str | None = None,
        candidates: list[Any] | None = None,
        raise_on_text: Exception | None = None,
    ) -> None:
        self._text = text
        self.candidates = candidates if candidates is not None else [object()]
        self._raise_on_text = raise_on_text

    @property
    def text(self) -> str:
        if self._raise_on_text is not None:
            raise self._raise_on_text
        if self._text is None:
            raise AttributeError("No text available")
        return self._text


class FakeModels:
    def __init__(self, response: Any = None, exc: Exception | None = None) -> None:
        self.response = response
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    async def generate_content(
        self,
        model: str,
        contents: str,
        config: dict[str, Any] | None = None,
    ) -> Any:
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.exc is not None:
            raise self.exc
        return self.response


class FakeAio:
    def __init__(self, models: FakeModels) -> None:
        self.models = models


class FakeClient:
    def __init__(self, response: Any = None, exc: Exception | None = None) -> None:
        self.models = FakeModels(response=response, exc=exc)
        self.aio = FakeAio(models=self.models)


@pytest.fixture
def dummy_score() -> ScoreResult:
    return ScoreResult(
        score=80,
        risk_level=RiskLevel.CRITICAL,
        rule_hits=[
            RuleHit(
                rule_id="DOMAIN_AGE_UNDER_7D",
                description="Domain was registered less than 7 days ago",
                points=30,
                evidence_refs=["age"],
            ),
            RuleHit(
                rule_id="VT_MALICIOUS_HIGH",
                description="VirusTotal malicious detections >= 5",
                points=50,
                evidence_refs=["vt"],
            ),
        ],
        total_points_before_clamp=80,
    )


# 10. Happy path
@pytest.mark.asyncio
async def test_gemini_explainer_happy_path(dummy_score: ScoreResult) -> None:
    fake_client = FakeClient(response=FakeResponse(text='{"narrative": "This is a narrative."}'))
    explainer = GeminiExplainer(api_key="test-api-key", client=fake_client)
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert result == "This is a narrative."
    assert len(fake_client.models.calls) == 1


# 11. Missing API key
@pytest.mark.asyncio
async def test_gemini_explainer_missing_api_key(
    monkeypatch: pytest.MonkeyPatch, dummy_score: ScoreResult
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        "dnscope.supervisor.gemini_explainer.Settings",
        lambda: Settings(gemini_api_key=None),
    )
    fake_client = FakeClient(response=FakeResponse(text='{"narrative": "Should not be called"}'))
    explainer = GeminiExplainer(api_key=None, client=fake_client)
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert result == "Narrative unavailable: GEMINI_API_KEY not set"
    assert len(fake_client.models.calls) == 0


# 12. Exception in SDK call
@pytest.mark.asyncio
async def test_gemini_explainer_sdk_exception(dummy_score: ScoreResult) -> None:
    fake_client = FakeClient(exc=RuntimeError("boom"))
    explainer = GeminiExplainer(api_key="test-api-key", client=fake_client)
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert result == "Narrative unavailable: RuntimeError: boom"


# 13. Malformed JSON response
@pytest.mark.asyncio
async def test_gemini_explainer_malformed_json_response(
    dummy_score: ScoreResult,
) -> None:
    fake_client = FakeClient(response=FakeResponse(text="not-json"))
    explainer = GeminiExplainer(api_key="test-api-key", client=fake_client)
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert result.startswith("Narrative unavailable: malformed response")


# 14. JSON but missing narrative key
@pytest.mark.asyncio
async def test_gemini_explainer_json_missing_narrative_key(
    dummy_score: ScoreResult,
) -> None:
    fake_client = FakeClient(response=FakeResponse(text='{"foo": "bar"}'))
    explainer = GeminiExplainer(api_key="test-api-key", client=fake_client)
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert result.startswith("Narrative unavailable: malformed response")


# 15. Empty candidates: simulate no candidates via attribute exception -> fallback, no raise
@pytest.mark.asyncio
async def test_gemini_explainer_empty_candidates_via_exception(
    dummy_score: ScoreResult,
) -> None:
    fake_client = FakeClient(
        response=FakeResponse(
            candidates=[],
            raise_on_text=AttributeError("No candidates available"),
        )
    )
    explainer = GeminiExplainer(api_key="test-api-key", client=fake_client)
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert result == "Narrative unavailable: malformed response"


# 16. Long narrative truncated to <= 2003 chars and ends with "..."
@pytest.mark.asyncio
async def test_gemini_explainer_truncation(dummy_score: ScoreResult) -> None:
    long_text = "A" * 2500
    fake_client = FakeClient(response=FakeResponse(text=json.dumps({"narrative": long_text})))
    explainer = GeminiExplainer(api_key="test-api-key", client=fake_client)
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert len(result) <= 2003
    assert len(result) == 2003
    assert result.endswith("...")
    assert result.startswith("A" * 2000)


# 17. Score never in output (score invariance with real explainer interface in supervisor loop)
@pytest.mark.asyncio
async def test_gemini_explainer_score_invariance_in_supervisor() -> None:
    fake_client = FakeClient(response=FakeResponse(text='{"narrative": "The score is 12."}'))
    explainer = GeminiExplainer(api_key="test-api-key", client=fake_client)
    supervisor = SupervisorAgent(explainer=explainer)

    reg_fresh = RegistrationFinding(status=AgentStatus.OK, age_days=3)  # +30 pts
    rep_malicious = ReputationFinding(status=AgentStatus.OK, detections_malicious=5)  # +50 pts

    assessment = await supervisor.assess(
        domain="example.com",
        dns=None,
        registration=reg_fresh,
        reputation=rep_malicious,
    )

    assert assessment.score_result.score == 80
    assert assessment.score_result.risk_level == RiskLevel.CRITICAL
    assert assessment.narrative == "The score is 12."


# 18. API key never logged or leaked
@pytest.mark.asyncio
async def test_gemini_explainer_api_key_never_leaked(dummy_score: ScoreResult) -> None:
    secret_key = "super_secret_gemini_key_12345"
    fake_client = FakeClient(
        response=FakeResponse(text='{"narrative": "Clean narrative without secret"}')
    )
    explainer = GeminiExplainer(api_key=secret_key, client=fake_client)

    # 1. repr check
    repr_str = repr(explainer)
    assert secret_key not in repr_str

    # 2. successful narrative check
    result = await explainer.explain("example.com", None, None, None, dummy_score)
    assert secret_key not in result

    # 3. exception error message check
    fake_error_client = FakeClient(exc=RuntimeError(f"Connection failed with key {secret_key}"))
    explainer_err = GeminiExplainer(api_key=secret_key, client=fake_error_client)
    err_result = await explainer_err.explain("example.com", None, None, None, dummy_score)
    assert secret_key not in err_result


# 19. Live test gated on GEMINI_API_KEY
@pytest.mark.gemini_live
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set",
)
@pytest.mark.asyncio
async def test_gemini_explainer_live(dummy_score: ScoreResult) -> None:
    explainer = GeminiExplainer()
    reg = RegistrationFinding(status=AgentStatus.OK, registrar="MarkMonitor", age_days=3)
    rep = ReputationFinding(
        status=AgentStatus.OK,
        detections_malicious=6,
        total_engines=90,
        categories=["phishing", "malicious"],
    )
    dns = DNSFinding(
        status=AgentStatus.OK,
        a_records=["192.0.2.1"],
        mx_records=["mail.target.com"],
    )

    narrative = await explainer.explain(
        domain="suspicious-domain-example.com",
        dns=dns,
        registration=reg,
        reputation=rep,
        score_result=dummy_score,
    )

    assert narrative is not None
    assert len(narrative) > 0
    assert not narrative.startswith("Narrative unavailable:")
    assert 50 <= len(narrative) <= 2003


def test_gemini_explainer_client_uses_v1beta() -> None:
    from unittest.mock import patch

    with patch("dnscope.supervisor.gemini_explainer.genai.Client") as mock_client:
        GeminiExplainer(api_key="fake")
        assert mock_client.call_count == 1
        _, kwargs = mock_client.call_args
        assert "http_options" in kwargs
        assert kwargs["http_options"].get("api_version") == "v1beta"
