from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.config import Settings
from dnscope.db.repository import ApiKeyRepository

from .models import ApiKeyContext, AuthError, Role
from .passwords import compute_hmac, compute_hmac_prefix, verify_api_key

__all__ = ["AuthError", "get_db_session", "require_admin", "require_api_key"]


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a session from request.app.state.session_factory; close on exit."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def require_api_key(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiKeyContext:
    """Validate X-API-Key header against hashed keys in Postgres with HMAC-prefix indexing.

    - Missing header -> 401 {"error": "missing_api_key"}
    - Look up by 16-char HMAC prefix -> O(1) in number of keys
    - Not found or argon2 verify fails -> 401 {"error": "invalid_api_key"}
    - Found but is_active=False -> 401 {"error": "api_key_disabled"}
    - Updates last_used_at
    - Attaches ApiKeyContext to request.state.api_key_context
    """
    settings: Settings = getattr(request.app.state, "settings", None) or Settings()
    header_name = settings.api_key_header_name
    raw_key = request.headers.get(header_name)

    if not raw_key or not raw_key.strip():
        raise AuthError(status.HTTP_401_UNAUTHORIZED, "missing_api_key")

    raw_key = raw_key.strip()
    secret = settings.api_key_hmac_secret
    hmac_prefix = compute_hmac_prefix(raw_key, secret)
    hmac_full = compute_hmac(raw_key, secret)

    repo = ApiKeyRepository(session)
    candidates = await repo.get_by_hmac_prefix(hmac_prefix)

    matched_key = None
    for cand in candidates:
        if verify_api_key(hmac_full, cand.key_hash):
            matched_key = cand
            break

    if matched_key is None:
        raise AuthError(status.HTTP_401_UNAUTHORIZED, "invalid_api_key")

    if not matched_key.is_active:
        raise AuthError(status.HTTP_401_UNAUTHORIZED, "api_key_disabled")

    await repo.update_last_used(matched_key.id)
    await session.commit()

    ctx = ApiKeyContext(
        key_id=matched_key.id,
        role=Role(matched_key.role),
        name=matched_key.name,
    )
    request.state.api_key_context = ctx
    return ctx


async def require_admin(
    ctx: Annotated[ApiKeyContext, Depends(require_api_key)],
) -> ApiKeyContext:
    """Require the authenticated API key to have ADMIN role."""
    if ctx.role != Role.ADMIN:
        raise AuthError(status.HTTP_403_FORBIDDEN, "admin_required")
    return ctx
