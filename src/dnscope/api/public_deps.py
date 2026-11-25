import hashlib
from typing import Annotated, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from dnscope.auth.rate_limit import InMemoryRateLimiter


def get_client_ip(request: Request) -> str:
    """Return client IP.

    Prefer X-Forwarded-For first hop (for when deployed behind a proxy).
    Fall back to request.client.host.
    Hash with SHA-256 before using as a rate-limit key — we do not want
    raw IPs in memory keys (privacy). Return `ip:<sha256_hex[:16]>`.
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        raw_ip = x_forwarded_for.split(",")[0].strip()
    elif request.client and request.client.host:
        raw_ip = request.client.host
    else:
        raw_ip = "127.0.0.1"

    hashed = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()[:16]
    return f"ip:{hashed}"


def get_public_limiter(request: Request) -> InMemoryRateLimiter:
    return request.app.state.public_limiter  # type: ignore[no-any-return]


async def check_public_rate_limit(
    request: Request,
    limiter: Annotated[InMemoryRateLimiter, Depends(get_public_limiter)],
) -> None:
    """Raise HTTPException(429) with Retry-After header if exceeded."""
    client_key = get_client_ip(request)
    allowed, retry_after = limiter.check(cast(UUID, client_key))
    if not allowed:
        retry_val = max(1, int(retry_after))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_val)},
        )

