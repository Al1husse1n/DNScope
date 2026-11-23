import pytest

from dnscope.schemas.common import AgentStatus
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding


@pytest.fixture
def dns_healthy() -> DNSFinding:
    return DNSFinding(
        agent_name="dns",
        status=AgentStatus.OK,
        a_records=["93.184.216.34"],
        aaaa_records=["2606:2800:220:1:248:1893:25c8:1946"],
        mx_records=["mail.example.com"],
        txt_records=["v=spf1 include:_spf.example.com ~all"],
        ns_records=["ns1.example.com", "ns2.example.com"],
        has_spf=True,
    )


@pytest.fixture
def dns_empty() -> DNSFinding:
    return DNSFinding(
        agent_name="dns",
        status=AgentStatus.OK,
        a_records=[],
        aaaa_records=[],
        mx_records=[],
        txt_records=[],
        ns_records=[],
        has_spf=False,
    )


@pytest.fixture
def dns_error() -> DNSFinding:
    return DNSFinding(
        agent_name="dns",
        status=AgentStatus.ERROR,
        errors=["timeout"],
    )


@pytest.fixture
def reg_fresh() -> RegistrationFinding:
    return RegistrationFinding(
        agent_name="registration",
        status=AgentStatus.OK,
        created_at="2026-11-20T12:00:00Z",
        expires_at="2027-11-20T12:00:00Z",
        registrar="MarkMonitor Inc.",
        age_days=3,
    )


@pytest.fixture
def reg_recent() -> RegistrationFinding:
    return RegistrationFinding(
        agent_name="registration",
        status=AgentStatus.OK,
        created_at="2026-11-03T12:00:00Z",
        expires_at="2027-11-03T12:00:00Z",
        registrar="MarkMonitor Inc.",
        age_days=20,
    )


@pytest.fixture
def reg_old() -> RegistrationFinding:
    return RegistrationFinding(
        agent_name="registration",
        status=AgentStatus.OK,
        created_at="2024-09-15T12:00:00Z",
        expires_at="2027-09-15T12:00:00Z",
        registrar="MarkMonitor Inc.",
        age_days=800,
    )


@pytest.fixture
def reg_unknown() -> RegistrationFinding:
    return RegistrationFinding(
        agent_name="registration",
        status=AgentStatus.PARTIAL,
        age_days=None,
        errors=["RDAP lookup partial"],
    )


@pytest.fixture
def rep_malicious() -> ReputationFinding:
    return ReputationFinding(
        agent_name="reputation",
        status=AgentStatus.OK,
        detections_malicious=12,
        detections_suspicious=0,
        total_engines=70,
        categories=["phishing", "malware"],
        permalink="https://virustotal.com/gui/domain/example.com",
    )


@pytest.fixture
def rep_clean() -> ReputationFinding:
    return ReputationFinding(
        agent_name="reputation",
        status=AgentStatus.OK,
        detections_malicious=0,
        detections_suspicious=0,
        total_engines=70,
        categories=[],
        permalink="https://virustotal.com/gui/domain/example.com",
    )


@pytest.fixture
def rep_error() -> ReputationFinding:
    return ReputationFinding(
        agent_name="reputation",
        status=AgentStatus.ERROR,
        errors=["VirusTotal API error: quota exceeded"],
    )
