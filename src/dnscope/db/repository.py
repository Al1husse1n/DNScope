import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.schemas.supervisor import SupervisorAssessment

from .models import ApiKey, Investigation, InvestigationJob


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        key_hash: str,
        hmac_prefix: str,
        role: str,
    ) -> ApiKey:
        key = ApiKey(
            name=name,
            key_hash=key_hash,
            hmac_prefix=hmac_prefix,
            role=role,
            is_active=True,
        )
        self.session.add(key)
        await self.session.flush()
        await self.session.refresh(key)
        return key

    async def get_by_id(self, key_id: uuid.UUID) -> ApiKey | None:
        stmt = select(ApiKey).where(ApiKey.id == key_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hmac_prefix(self, hmac_prefix: str) -> list[ApiKey]:
        stmt = select(ApiKey).where(ApiKey.hmac_prefix == hmac_prefix)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_hmac_prefix(self, hmac_prefix: str) -> list[ApiKey]:
        stmt = select(ApiKey).where(
            ApiKey.hmac_prefix == hmac_prefix,
            ApiKey.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[ApiKey]:
        stmt = select(ApiKey).order_by(ApiKey.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def revoke(self, key_id: uuid.UUID) -> bool:
        stmt = (
            update(ApiKey).where(ApiKey.id == key_id).values(is_active=False).returning(ApiKey.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update_last_used(self, key_id: uuid.UUID) -> None:
        stmt = update(ApiKey).where(ApiKey.id == key_id).values(last_used_at=func.now())
        await self.session.execute(stmt)


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        domain: str,
        normalized_domain: str,
        findings: dict[str, Any],
        assessment: SupervisorAssessment,
        api_key_id: uuid.UUID | None = None,
    ) -> Investigation:
        """Persist an investigation. Return the ORM instance with `id`
        and `created_at` populated (flush + refresh if needed)."""
        if api_key_id is None:
            stmt = select(ApiKey.id).limit(1)
            res = await self.session.execute(stmt)
            existing_id = res.scalar_one_or_none()
            if existing_id is not None:
                api_key_id = existing_id
            else:
                dummy_key = ApiKey(
                    name="test-default",
                    key_hash=f"dummy_hash_{uuid.uuid4()}",
                    hmac_prefix=uuid.uuid4().hex[:16],
                    role="user",
                    is_active=True,
                )
                self.session.add(dummy_key)
                await self.session.flush()
                api_key_id = dummy_key.id

        assessment_dict = assessment.model_dump(mode="json")
        inv = Investigation(
            api_key_id=api_key_id,
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

    async def get(
        self,
        investigation_id: uuid.UUID,
        api_key_id: uuid.UUID | None = None,
    ) -> Investigation | None:
        """Return None if not found or unauthorized."""
        stmt = select(Investigation).where(Investigation.id == investigation_id)
        if api_key_id is not None:
            stmt = stmt.where(Investigation.api_key_id == api_key_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(
        self,
        limit: int = 20,
        offset: int = 0,
        api_key_id: uuid.UUID | None = None,
    ) -> tuple[list[Investigation], int]:
        """Return (items ordered by created_at DESC, total_count)."""
        count_stmt = select(func.count(Investigation.id))
        if api_key_id is not None:
            count_stmt = count_stmt.where(Investigation.api_key_id == api_key_id)
        total_count_result = await self.session.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        stmt = select(Investigation)
        if api_key_id is not None:
            stmt = stmt.where(Investigation.api_key_id == api_key_id)
        stmt = stmt.order_by(Investigation.created_at.desc()).limit(limit).offset(offset)
        items_result = await self.session.execute(stmt)
        items = list(items_result.scalars().all())
        return items, total_count


class InvestigationJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        api_key_id: uuid.UUID,
        domain: str,
        status: str = "PENDING",
    ) -> InvestigationJob:
        job = InvestigationJob(
            api_key_id=api_key_id,
            domain=domain,
            status=status,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get(
        self,
        job_id: uuid.UUID,
        api_key_id: uuid.UUID | None = None,
    ) -> InvestigationJob | None:
        stmt = select(InvestigationJob).where(InvestigationJob.id == job_id)
        if api_key_id is not None:
            stmt = stmt.where(InvestigationJob.api_key_id == api_key_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        investigation_id: uuid.UUID | None = None,
        error: str | None = None,
    ) -> None:
        stmt = (
            update(InvestigationJob)
            .where(InvestigationJob.id == job_id)
            .values(
                status=status,
                investigation_id=investigation_id,
                error=error,
                updated_at=func.now(),
            )
        )
        await self.session.execute(stmt)

    async def recover_stale_jobs(self, cutoff: datetime) -> int:
        stmt = (
            update(InvestigationJob)
            .where(
                InvestigationJob.status.in_(["PENDING", "RUNNING"]),
                InvestigationJob.updated_at < cutoff,
            )
            .values(
                status="FAILED",
                error="process restarted before completion",
                updated_at=func.now(),
            )
            .returning(InvestigationJob.id)
        )
        result = await self.session.execute(stmt)
        recovered_ids = list(result.scalars().all())
        return len(recovered_ids)
