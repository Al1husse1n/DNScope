import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from dnscope.api.deps import get_repository
from dnscope.api.schemas import (
    CreateInvestigationRequest,
    InvestigationResponse,
    InvestigationSummary,
    ListInvestigationsResponse,
)
from dnscope.db.repository import InvestigationRepository
from dnscope.schemas.supervisor import SupervisorAssessment
from dnscope.validation import validate_domain

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=InvestigationResponse,
)
async def create_investigation(
    payload: CreateInvestigationRequest,
    request: Request,
    repo: Annotated[InvestigationRepository, Depends(get_repository)],
) -> InvestigationResponse | JSONResponse:
    """Run the full investigation graph, persist, and return.

    Flow:
      1. Validate domain via validate_domain (raise DomainValidationError -> 400).
      2. Build initial graph state: {"domain": payload.domain}.
      3. Invoke request.app.state.graph.ainvoke(state) wrapped in
         asyncio.wait_for(..., timeout=timeout). Timeout -> 504.
      4. If state["assessment"] is None -> 400.
      5. Persist via repo.create(...).
      6. Return InvestigationResponse with id, domain, normalized_domain,
         created_at, assessment.
    """
    validated = validate_domain(payload.domain)
    normalized_domain = validated.normalized
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
    )
    await repo.session.commit()

    return InvestigationResponse(
        id=inv.id,
        domain=inv.domain,
        normalized_domain=inv.normalized_domain,
        created_at=inv.created_at,
        assessment=assessment,
    )


@router.get("", response_model=ListInvestigationsResponse)
async def list_investigations(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    repo: Annotated[InvestigationRepository, Depends(get_repository)] = None,  # type: ignore[assignment]
) -> ListInvestigationsResponse:
    """Paginated list, ordered by created_at DESC."""
    items, total = await repo.list_recent(limit=limit, offset=offset)
    summary_items = [
        InvestigationSummary(
            id=item.id,
            domain=item.domain,
            normalized_domain=item.normalized_domain,
            risk_score=item.risk_score,
            risk_level=item.risk_level,
            created_at=item.created_at,
        )
        for item in items
    ]
    return ListInvestigationsResponse(
        items=summary_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    repo: Annotated[InvestigationRepository, Depends(get_repository)],
) -> InvestigationResponse:
    """404 if not found."""
    inv = await repo.get(investigation_id)
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
