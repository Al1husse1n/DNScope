from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, **kwargs: Any) -> AsyncEngine:
    """create_async_engine(database_url, echo=False, pool_pre_ping=True)."""
    return create_async_engine(database_url, echo=False, pool_pre_ping=True, **kwargs)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker(engine, expire_on_commit=False)."""
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
