from typing import Optional

from pydantic import BaseModel, Field

from .common import AgentStatus, Evidence


class BaseAgentFinding(BaseModel):
    agent_name: str
    status: AgentStatus
    errors: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    duration_ms: Optional[int] = None


class DNSFinding(BaseAgentFinding):
    agent_name: str = "dns"
    a_records: list[str] = []
    aaaa_records: list[str] = []
    mx_records: list[str] = []
    txt_records: list[str] = []
    ns_records: list[str] = []
    has_spf: Optional[bool] = None


class RegistrationFinding(BaseAgentFinding):
    agent_name: str = "registration"
    created_at: Optional[str] = None  # ISO date string from RDAP
    expires_at: Optional[str] = None
    registrar: Optional[str] = None
    age_days: Optional[int] = None


class ReputationFinding(BaseAgentFinding):
    agent_name: str = "reputation"
    detections_malicious: Optional[int] = None
    detections_suspicious: Optional[int] = None
    total_engines: Optional[int] = None
    categories: list[str] = []
    permalink: Optional[str] = None
