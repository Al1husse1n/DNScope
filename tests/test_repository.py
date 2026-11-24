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
