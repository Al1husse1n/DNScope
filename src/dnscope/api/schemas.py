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


# --- Jobs schemas ---


class CreateJobResponse(BaseModel):
    job_id: UUID
    status: str


class JobResponse(BaseModel):
    job_id: UUID
    status: str
    domain: str
    investigation_id: UUID | None
    error: str | None
    created_at: datetime
    updated_at: datetime


# --- Auth & Admin schemas ---


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(pattern="^(admin|user)$")


class CreatedApiKeyResponse(BaseModel):
    id: UUID
    name: str
    role: str
    api_key: str
    created_at: datetime


class ApiKeySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
