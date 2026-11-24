import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from dnscope.api.deps import get_api_key_repository
from dnscope.api.schemas import ApiKeySummary, CreateApiKeyRequest, CreatedApiKeyResponse
from dnscope.auth.dependencies import require_admin
from dnscope.auth.models import ApiKeyContext
from dnscope.auth.passwords import (
    compute_hmac,
    compute_hmac_prefix,
    generate_api_key,
    hash_api_key,
)
from dnscope.config import Settings
from dnscope.db.repository import ApiKeyRepository

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/api-keys",
    response_model=CreatedApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    payload: CreateApiKeyRequest,
    request: Request,
    ctx: Annotated[ApiKeyContext, Depends(require_admin)] = None,  # type: ignore[assignment]
    repo: Annotated[ApiKeyRepository, Depends(get_api_key_repository)] = None,  # type: ignore[assignment]
) -> CreatedApiKeyResponse:
    """Generate raw key, store HMAC + argon2 hash, return raw key ONCE."""
    settings: Settings = getattr(request.app.state, "settings", None) or Settings()
    raw_key = generate_api_key()
    secret = settings.api_key_hmac_secret
    hmac_key = compute_hmac(raw_key, secret)
    hmac_prefix = compute_hmac_prefix(raw_key, secret)
    stored_hash = hash_api_key(hmac_key)

    api_key_row = await repo.create(
        name=payload.name,
        key_hash=stored_hash,
        hmac_prefix=hmac_prefix,
        role=payload.role,
    )
    await repo.session.commit()

    return CreatedApiKeyResponse(
        id=api_key_row.id,
        name=api_key_row.name,
        role=api_key_row.role,
        api_key=raw_key,
        created_at=api_key_row.created_at,
    )


@router.get("/api-keys", response_model=list[ApiKeySummary])
async def list_api_keys(
    ctx: Annotated[ApiKeyContext, Depends(require_admin)] = None,  # type: ignore[assignment]
    repo: Annotated[ApiKeyRepository, Depends(get_api_key_repository)] = None,  # type: ignore[assignment]
) -> list[ApiKeySummary]:
    """List keys WITHOUT raw value or key_hash."""
    keys = await repo.list_all()
    return [ApiKeySummary.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    ctx: Annotated[ApiKeyContext, Depends(require_admin)] = None,  # type: ignore[assignment]
    repo: Annotated[ApiKeyRepository, Depends(get_api_key_repository)] = None,  # type: ignore[assignment]
) -> Response:
    """Soft-delete: set is_active=False. Does not delete row."""
    revoked = await repo.revoke(key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    await repo.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
