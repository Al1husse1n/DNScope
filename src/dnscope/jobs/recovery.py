import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.db.repository import InvestigationJobRepository

logger = logging.getLogger("dnscope.jobs.recovery")


async def recover_stale_jobs(session: AsyncSession, stale_seconds: int = 60) -> int:
    """On startup, mark any InvestigationJob with status in (PENDING, RUNNING)
    and updated_at older than `now - stale_seconds` as FAILED with
    error = "process restarted before completion". Return count. Log at WARNING.
    """
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=stale_seconds)
    repo = InvestigationJobRepository(session)
    count = await repo.recover_stale_jobs(cutoff)
    if count > 0:
        await session.commit()
        logger.warning(
            "Recovered %d stale jobs (updated_at older than %d seconds)", count, stale_seconds
        )
    return count
