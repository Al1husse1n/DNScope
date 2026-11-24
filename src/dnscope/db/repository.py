import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.schemas.supervisor import SupervisorAssessment

from .models import Investigation


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        domain: str,
        normalized_domain: str,
        findings: dict[str, Any],
        assessment: SupervisorAssessment,
    ) -> Investigation:
        """Persist an investigation. Return the ORM instance with `id`
        and `created_at` populated (flush + refresh if needed)."""
        assessment_dict = assessment.model_dump(mode="json")
        inv = Investigation(
            domain=domain,
            normalized_domain=normalized_domain,
            risk_score=assessment.score_result.score,
            risk_level=assessment.score_result.risk_level.value,
            findings=findings,
            assessment=assessment_dict,
        )
        self.session.add(inv)
        await self.session.flush()
        await self.session.refresh(inv)
        return inv

    async def get(self, investigation_id: uuid.UUID) -> Investigation | None:
        """Return None if not found."""
        stmt = select(Investigation).where(Investigation.id == investigation_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Investigation], int]:
        """Return (items ordered by created_at DESC, total_count)."""
        count_stmt = select(func.count(Investigation.id))
        total_count_result = await self.session.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        stmt = (
            select(Investigation)
            .order_by(Investigation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().all())
        return items, total_count
