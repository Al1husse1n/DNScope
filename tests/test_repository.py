import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.db.repository import InvestigationRepository
from dnscope.schemas.common import RiskLevel
from dnscope.schemas.scoring import RuleHit, ScoreResult
from dnscope.schemas.supervisor import SupervisorAssessment


def make_assessment(score: int = 50, narrative: str = "Test narrative") -> SupervisorAssessment:
    return SupervisorAssessment(
        score_result=ScoreResult(
            score=score,
            risk_level=RiskLevel.MEDIUM if score < 70 else RiskLevel.HIGH,
            rule_hits=[
                RuleHit(
                    rule_id="RULE_TEST",
                    description="Test rule description",
                    points=score,
                    evidence_refs=["ref1"],
                )
            ],
            total_points_before_clamp=score,
        ),
        rule_trace_explanation="Rule trace explanation string",
        narrative=narrative,
        inconclusive_checks=[],
    )


# 1. create returns row with UUID id and non-null created_at
@pytest.mark.asyncio
async def test_repository_create(db_session: AsyncSession) -> None:
    repo = InvestigationRepository(db_session)
    assessment = make_assessment(60)
    findings: dict[str, Any] = {"dns": {"a_records": ["1.2.3.4"]}, "test_key": "val"}

    inv = await repo.create(
        domain="example.com",
        normalized_domain="example.com",
        findings=findings,
        assessment=assessment,
    )

    assert isinstance(inv.id, uuid.UUID)
    assert inv.created_at is not None
    assert inv.domain == "example.com"
    assert inv.normalized_domain == "example.com"
    assert inv.risk_score == 60
    assert inv.risk_level == "MEDIUM"


# 2. get returns the row
@pytest.mark.asyncio
async def test_repository_get_found(db_session: AsyncSession) -> None:
    repo = InvestigationRepository(db_session)
    assessment = make_assessment(80)
    inv = await repo.create(
        domain="target.com",
        normalized_domain="target.com",
        findings={},
        assessment=assessment,
    )

    fetched = await repo.get(inv.id)
    assert fetched is not None
    assert fetched.id == inv.id
    assert fetched.domain == "target.com"
    assert fetched.risk_score == 80


# 3. get with random UUID returns None
@pytest.mark.asyncio
async def test_repository_get_not_found(db_session: AsyncSession) -> None:
    repo = InvestigationRepository(db_session)
    random_id = uuid.uuid4()
    fetched = await repo.get(random_id)
    assert fetched is None


# 4. list_recent returns ordered by created_at DESC, total count correct
@pytest.mark.asyncio
async def test_repository_list_recent_ordering(db_session: AsyncSession) -> None:
    repo = InvestigationRepository(db_session)
    inv1 = await repo.create("d1.com", "d1.com", {}, make_assessment(10))
    inv2 = await repo.create("d2.com", "d2.com", {}, make_assessment(20))
    inv3 = await repo.create("d3.com", "d3.com", {}, make_assessment(30))

    items, total = await repo.list_recent(limit=10, offset=0)
    assert total >= 3
    ids = [item.id for item in items]
    assert ids.index(inv3.id) < ids.index(inv2.id) < ids.index(inv1.id)


# 5. list_recent limit/offset works
@pytest.mark.asyncio
async def test_repository_list_recent_pagination(db_session: AsyncSession) -> None:
    repo = InvestigationRepository(db_session)
    for i in range(5):
        await repo.create(f"page{i}.com", f"page{i}.com", {}, make_assessment(i * 10))

    page1, total1 = await repo.list_recent(limit=2, offset=0)
    assert len(page1) == 2
    assert total1 >= 5

    page2, _total2 = await repo.list_recent(limit=2, offset=2)
    assert len(page2) == 2
    assert page1[0].id != page2[0].id


# 6. Findings + assessment round-trip through JSONB without loss
@pytest.mark.asyncio
async def test_repository_jsonb_roundtrip(db_session: AsyncSession) -> None:
    repo = InvestigationRepository(db_session)
    complex_findings: dict[str, Any] = {
        "nested": {"level2": {"level3": [1, 2, "unicode: 🚀 ñ 世界"]}},
        "null_val": None,
        "bool_val": True,
        "empty_list": [],
    }
    assessment = make_assessment(75, narrative="Narrative with unicode: 🛡️ threat-detected")

    inv = await repo.create(
        domain="unicode.com",
        normalized_domain="unicode.com",
        findings=complex_findings,
        assessment=assessment,
    )

    fetched = await repo.get(inv.id)
    assert fetched is not None
    assert fetched.findings == complex_findings
    assert fetched.assessment["narrative"] == "Narrative with unicode: 🛡️ threat-detected"
    assert fetched.assessment["score_result"]["score"] == 75


# 7. ApiKeyRepository CRUD
@pytest.mark.asyncio
async def test_api_key_repository_crud(db_session: AsyncSession) -> None:
    from dnscope.db.repository import ApiKeyRepository

    repo = ApiKeyRepository(db_session)
    key = await repo.create(
        name="repo-key-1",
        key_hash=f"hash_{uuid.uuid4()}",
        hmac_prefix="repo123456789012",
        role="user",
    )
    assert key.id is not None
    assert key.is_active is True

    fetched = await repo.get_by_id(key.id)
    assert fetched is not None
    assert fetched.name == "repo-key-1"

    all_keys = await repo.list_all()
    assert any(k.id == key.id for k in all_keys)


# 8. ApiKeyRepository revoke and active lookup
@pytest.mark.asyncio
async def test_api_key_repository_revoke(db_session: AsyncSession) -> None:
    from dnscope.db.repository import ApiKeyRepository

    repo = ApiKeyRepository(db_session)
    key = await repo.create(
        name="repo-key-revoke",
        key_hash=f"hash_{uuid.uuid4()}",
        hmac_prefix="repo123456789099",
        role="user",
    )
    active_before = await repo.get_active_by_hmac_prefix("repo123456789099")
    assert len(active_before) == 1

    revoked = await repo.revoke(key.id)
    assert revoked is True

    active_after = await repo.get_active_by_hmac_prefix("repo123456789099")
    assert len(active_after) == 0


# 9. ApiKeyRepository update_last_used
@pytest.mark.asyncio
async def test_api_key_repository_update_last_used(db_session: AsyncSession) -> None:
    from dnscope.db.repository import ApiKeyRepository

    repo = ApiKeyRepository(db_session)
    key = await repo.create(
        name="repo-key-lastused",
        key_hash=f"hash_{uuid.uuid4()}",
        hmac_prefix="repo123456789088",
        role="user",
    )
    assert key.last_used_at is None

    await repo.update_last_used(key.id)
    fetched = await repo.get_by_id(key.id)
    assert fetched is not None
    assert fetched.last_used_at is not None


# 10. InvestigationJobRepository CRUD and update_status
@pytest.mark.asyncio
async def test_job_repository_crud(db_session: AsyncSession) -> None:
    from dnscope.db.repository import ApiKeyRepository, InvestigationJobRepository

    key_repo = ApiKeyRepository(db_session)
    k = await key_repo.create("job-user", f"hash_{uuid.uuid4()}", "jobprefix123456", "user")

    job_repo = InvestigationJobRepository(db_session)
    job = await job_repo.create(api_key_id=k.id, domain="job-test.com")
    assert job.status == "PENDING"

    await job_repo.update_status(job.id, status="FAILED", error="test failure")

    fetched = await job_repo.get(job.id)
    assert fetched is not None
    assert fetched.status == "FAILED"
    assert fetched.error == "test failure"


# 11. InvestigationJobRepository tenant isolation
@pytest.mark.asyncio
async def test_job_repository_tenant_isolation(db_session: AsyncSession) -> None:
    from dnscope.db.repository import ApiKeyRepository, InvestigationJobRepository

    key_repo = ApiKeyRepository(db_session)
    k1 = await key_repo.create("job-user1", f"hash_{uuid.uuid4()}", "jobprefix123451", "user")
    k2 = await key_repo.create("job-user2", f"hash_{uuid.uuid4()}", "jobprefix123452", "user")

    job_repo = InvestigationJobRepository(db_session)
    job1 = await job_repo.create(api_key_id=k1.id, domain="tenant-job.com")

    # Fetch with key1 -> found
    assert await job_repo.get(job1.id, api_key_id=k1.id) is not None
    # Fetch with key2 -> None
    assert await job_repo.get(job1.id, api_key_id=k2.id) is None
