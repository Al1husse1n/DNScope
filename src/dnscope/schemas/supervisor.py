from typing import Optional

from pydantic import BaseModel, Field

from .scoring import ScoreResult


class InconclusiveCheck(BaseModel):
    agent_name: str
    reason: str


class SupervisorAssessment(BaseModel):
    """Structured output of the supervisor node.

    `score_result` MUST be the exact ScoreResult from the deterministic scoring
    engine. It is populated before any LLM is invoked, and it is validated after
    any LLM call to be byte-identical to the pre-LLM value. The LLM cannot
    override the numeric score.
    """

    score_result: ScoreResult
    rule_trace_explanation: str  # human-readable, deterministic string
    narrative: Optional[str] = None  # LLM-authored in P3.5+, None in P3
    inconclusive_checks: list[InconclusiveCheck] = Field(default_factory=list)


class InvestigationResult(BaseModel):
    """The full result returned by the graph."""

    domain: str
    normalized_domain: str
    assessment: SupervisorAssessment
