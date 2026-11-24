from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.auth.dependencies import get_db_session
from dnscope.auth.rate_limit import InMemoryRateLimiter
from dnscope.db.repository import (
    ApiKeyRepository,
    InvestigationJobRepository,
    InvestigationRepository,
)
from dnscope.jobs.runner import JobRunner


async def get_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationRepository:
    return InvestigationRepository(session)


async def get_api_key_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiKeyRepository:
    return ApiKeyRepository(session)


async def get_job_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationJobRepository:
    return InvestigationJobRepository(session)


def get_rate_limiter(request: Request) -> InMemoryRateLimiter:
    return request.app.state.rate_limiter  # type: ignore[no-any-return]


def get_job_runner(request: Request) -> JobRunner:
    return request.app.state.job_runner  # type: ignore[no-any-return]
