from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, **kwargs: Any) -> AsyncEngine:
    """Create an async SQLAlchemy engine, normalizing Neon/asyncpg URLs and SSL."""
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if "sslmode=" in database_url or "channel_binding=" in database_url:
        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        query.pop("sslmode", None)
        query.pop("channel_binding", None)
        database_url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

    connect_args = dict(kwargs.pop("connect_args", {}))
    if "neon.tech" in database_url:
        connect_args.setdefault("ssl", "require")

    return create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
        **kwargs,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker(engine, expire_on_commit=False)."""
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
