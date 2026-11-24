import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from dnscope.api.deps import (
    get_job_repository,
    get_job_runner,
    get_rate_limiter,
    get_repository,
)
from dnscope.api.schemas import (
    CreateInvestigationRequest,
    InvestigationResponse,
    InvestigationSummary,
    ListInvestigationsResponse,
)
from dnscope.auth.dependencies import require_api_key
from dnscope.auth.models import ApiKeyContext, Role
from dnscope.auth.rate_limit import InMemoryRateLimiter
from dnscope.db.repository import InvestigationJobRepository, InvestigationRepository
from dnscope.jobs.runner import JobRunner
from dnscope.schemas.supervisor import SupervisorAssessment
from dnscope.validation import validate_domain

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_investigation_async(
    payload: CreateInvestigationRequest,
    request: Request,
    sync: bool = Query(False),
    ctx: Annotated[ApiKeyContext, Depends(require_api_key)] = None,  # type: ignore[assignment]
    limiter: Annotated[InMemoryRateLimiter, Depends(get_rate_limiter)] = None,  # type: ignore[assignment]
    repo: Annotated[InvestigationRepository, Depends(get_repository)] = None,  # type: ignore[assignment]
    job_repo: Annotated[InvestigationJobRepository, Depends(get_job_repository)] = None,  # type: ignore[assignment]
    job_runner: Annotated[JobRunner, Depends(get_job_runner)] = None,  # type: ignore[assignment]
) -> JSONResponse:
    """If sync=True: run inline (P4 behavior), rate limit still applies,
       persist investigation with api_key_id=ctx.key_id, return 201 with
       full InvestigationResponse.
       If sync=False: rate limit, validate domain (400 on failure, before
       creating a job), create InvestigationJob (PENDING), enqueue to
       JobRunner, return 202 with {"job_id": ..., "status": "PENDING"}.
    Rate limit check happens BEFORE any work; exceeded -> 429 with
    Retry-After header (integer seconds, ceil).
    """
    # 1. Rate limit check
    allowed, retry_after = limiter.check(ctx.key_id)
    if not allowed:
        retry_int = int(retry_after)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_int)},
            content={"error": "rate_limited", "retry_after": retry_int},
        )

    # 2. Validate domain before enqueuing or running
    validated = validate_domain(payload.domain)
    normalized_domain = validated.normalized

    # 3. Synchronous branch
    if sync:
        state = {"domain": payload.domain}
        timeout = getattr(request.app.state, "investigation_timeout", 60.0)
        result_state = await asyncio.wait_for(
            request.app.state.graph.ainvoke(state),
            timeout=timeout,
        )

        assessment = result_state.get("assessment")
        if assessment is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "graph_error", "detail": "assessment was None"},
            )

        findings_dict = {
            "dns": (
                result_state.get("dns").model_dump(mode="json") if result_state.get("dns") else None
            ),
            "registration": (
                result_state.get("registration").model_dump(mode="json")
                if result_state.get("registration")
                else None
            ),
            "reputation": (
                result_state.get("reputation").model_dump(mode="json")
                if result_state.get("reputation")
                else None
            ),
        }

        inv = await repo.create(
            domain=payload.domain,
            normalized_domain=normalized_domain,
            findings=findings_dict,
            assessment=assessment,
            api_key_id=ctx.key_id,
        )
        await repo.session.commit()

        resp = InvestigationResponse(
            id=inv.id,
            domain=inv.domain,
            normalized_domain=inv.normalized_domain,
            created_at=inv.created_at,
            assessment=assessment,
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=resp.model_dump(mode="json"),
        )

    # 4. Asynchronous branch (default)
    job = await job_repo.create(
        api_key_id=ctx.key_id,
        domain=payload.domain,
        status="PENDING",
    )
    await job_repo.session.commit()
    await job_runner.start(job.id, payload.domain, ctx.key_id)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"job_id": str(job.id), "status": "PENDING"},
    )


@router.get("", response_model=ListInvestigationsResponse)
async def list_investigations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: Annotated[ApiKeyContext, Depends(require_api_key)] = None,  # type: ignore[assignment]
    repo: Annotated[InvestigationRepository, Depends(get_repository)] = None,  # type: ignore[assignment]
) -> ListInvestigationsResponse:
    """Paginated list, ordered by created_at DESC with tenant isolation."""
    api_key_id = None if ctx.role == Role.ADMIN else ctx.key_id
    items, total = await repo.list_recent(limit=limit, offset=offset, api_key_id=api_key_id)
    return ListInvestigationsResponse(
        items=[InvestigationSummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    ctx: Annotated[ApiKeyContext, Depends(require_api_key)] = None,  # type: ignore[assignment]
    repo: Annotated[InvestigationRepository, Depends(get_repository)] = None,  # type: ignore[assignment]
) -> InvestigationResponse:
    """404 if not found or unauthorized."""
    api_key_id = None if ctx.role == Role.ADMIN else ctx.key_id
    inv = await repo.get(investigation_id, api_key_id=api_key_id)
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )

    assessment = SupervisorAssessment.model_validate(inv.assessment)
    return InvestigationResponse(
        id=inv.id,
        domain=inv.domain,
        normalized_domain=inv.normalized_domain,
        created_at=inv.created_at,
        assessment=assessment,
    )
