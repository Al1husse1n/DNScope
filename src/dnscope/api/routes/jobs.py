import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from dnscope.api.deps import get_job_repository
from dnscope.api.schemas import JobResponse
from dnscope.auth.dependencies import require_api_key
from dnscope.auth.models import ApiKeyContext, Role
from dnscope.db.repository import InvestigationJobRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    ctx: Annotated[ApiKeyContext, Depends(require_api_key)] = None,  # type: ignore[assignment]
    job_repo: Annotated[InvestigationJobRepository, Depends(get_job_repository)] = None,  # type: ignore[assignment]
) -> JobResponse:
    """Return job status. Non-admin can only see own jobs (404 otherwise)."""
    api_key_id = None if ctx.role == Role.ADMIN else ctx.key_id
    job = await job_repo.get(job_id, api_key_id=api_key_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return JobResponse(
        job_id=job.id,
        status=job.status,
        domain=job.domain,
        investigation_id=job.investigation_id,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
