from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.db.repository import InvestigationRepository


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a session from request.app.state.session_factory; close on exit."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def get_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> InvestigationRepository:
    return InvestigationRepository(session)
