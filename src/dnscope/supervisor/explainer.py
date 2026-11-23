from typing import Protocol

from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import ScoreResult


class Explainer(Protocol):
    async def explain(
        self,
        domain: str,
        dns: DNSFinding | None,
        registration: RegistrationFinding | None,
        reputation: ReputationFinding | None,
        score_result: ScoreResult,
    ) -> str:
        """Return a narrative explanation of the deterministic score.

        Implementations MUST NOT modify the score. They only narrate.
        Implementations MUST be pure-async and MUST NOT raise — if the
        LLM call fails, return a short fallback string like
        'Narrative unavailable: <reason>'.
        """
        ...


class NullExplainer:
    """No-op explainer used in P3. Returns a fixed string."""

    async def explain(
        self,
        domain: str,
        dns: DNSFinding | None,
        registration: RegistrationFinding | None,
        reputation: ReputationFinding | None,
        score_result: ScoreResult,
    ) -> str:
        return "Narrative generation not enabled."
