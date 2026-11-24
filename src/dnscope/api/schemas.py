from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dnscope.schemas.supervisor import SupervisorAssessment


class CreateInvestigationRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=512)


class InvestigationResponse(BaseModel):
    """Full detail response for a single investigation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    normalized_domain: str
    created_at: datetime
    assessment: SupervisorAssessment


class InvestigationSummary(BaseModel):
    """Lightweight list item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain: str
    normalized_domain: str
    risk_score: int
    risk_level: str
    created_at: datetime


class ListInvestigationsResponse(BaseModel):
    items: list[InvestigationSummary]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    status: str
    db: str
