from typing import Optional, TypedDict

from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.supervisor import SupervisorAssessment


class GraphState(TypedDict, total=False):
    domain: str
    normalized_domain: str
    dns: Optional[DNSFinding]
    registration: Optional[RegistrationFinding]
    reputation: Optional[ReputationFinding]
    assessment: Optional[SupervisorAssessment]
