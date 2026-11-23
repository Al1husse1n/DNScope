from pydantic import BaseModel

from .common import RiskLevel


class RuleHit(BaseModel):
    rule_id: str
    description: str
    points: int  # can be negative (benign offset)
    evidence_refs: list[str] = []  # labels of evidence that triggered it


class ScoreResult(BaseModel):
    score: int  # 0..100, clamped
    risk_level: RiskLevel
    rule_hits: list[RuleHit]
    total_points_before_clamp: int
