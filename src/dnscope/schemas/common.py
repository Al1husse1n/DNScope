from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AgentStatus(str, Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"  # some checks succeeded, some failed
    ERROR = "ERROR"  # agent failed entirely
    SKIPPED = "SKIPPED"  # e.g. missing API key


class EvidenceCategory(str, Enum):
    MALICIOUS = "MALICIOUS"
    SUSPICIOUS = "SUSPICIOUS"
    BENIGN = "BENIGN"
    INCONCLUSIVE = "INCONCLUSIVE"


class Evidence(BaseModel):
    category: EvidenceCategory
    label: str
    detail: str
    source: str  # e.g. "dns", "rdap", "virustotal"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
