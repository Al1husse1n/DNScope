import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.db.models import PublicInvestigation


class PublicResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        domain: str,
        normalized_domain: str,
        result: dict[str, Any],
        ttl_seconds: int,
    ) -> PublicInvestigation:
        """Insert row with expires_at = now() + ttl_seconds. Return the row."""
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        share_id = uuid.UUID(result["share_id"]) if "share_id" in result else uuid.uuid4()
        record = PublicInvestigation(
            share_id=share_id,
            domain=domain,
            normalized_domain=normalized_domain,
            result=result,
            expires_at=expires_at,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get(self, share_id: uuid.UUID) -> PublicInvestigation | None:
        """Return row if exists AND expires_at > now(). Delete lazily if expired (best-effort)."""
        stmt = select(PublicInvestigation).where(PublicInvestigation.share_id == share_id)
        res = await self._session.execute(stmt)
        record = res.scalar_one_or_none()
        if record is None:
            return None

        now = datetime.now(UTC)
        if record.expires_at <= now:
            await self._session.delete(record)
            await self._session.commit()
            return None

        return record

    async def delete_expired(self) -> int:
        """Delete rows where expires_at < now(). Return count. Called opportunistically from a background task, not on every request."""
        now = datetime.now(UTC)
        stmt = delete(PublicInvestigation).where(PublicInvestigation.expires_at < now)
        res = await self._session.execute(stmt)
        await self._session.commit()
        assert isinstance(res, CursorResult)
        return int(res.rowcount or 0)

