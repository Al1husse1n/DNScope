from typing import Optional

from pydantic import BaseModel, Field

from .findings import DNSFinding, RegistrationFinding, ReputationFinding
from .scoring import ScoreResult


class InvestigationFindings(BaseModel):
    dns: Optional[DNSFinding] = None
    registration: Optional[RegistrationFinding] = None
    reputation: Optional[ReputationFinding] = None


class InvestigationState(BaseModel):
    domain: str
    normalized_domain: str
    findings: InvestigationFindings = Field(default_factory=InvestigationFindings)
    score: Optional[ScoreResult] = None
    # LLM-authored narrative fields are added in P3, not now.
