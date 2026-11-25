import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from dnscope.api.public_deps import check_public_rate_limit
from dnscope.api.schemas import CreateInvestigationRequest
from dnscope.auth.dependencies import get_db_session
from dnscope.config import Settings
from dnscope.db.public_repository import PublicResultRepository
from dnscope.graph.workflow import build_investigation_graph
from dnscope.schemas.supervisor import SupervisorAssessment
from dnscope.supervisor.agent import SupervisorAgent
from dnscope.supervisor.explainer import NullExplainer
from dnscope.validation import validate_domain

router = APIRouter(tags=["public"])


@router.post("/investigate", status_code=status.HTTP_201_CREATED)
async def public_investigate(
    payload: CreateInvestigationRequest,
    request: Request,
    _: Annotated[None, Depends(check_public_rate_limit)] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> JSONResponse:
    """Anonymous investigation. No auth. IP rate-limited."""
    # 1. Validate domain -> 400 on invalid (before any work)
    norm_domain = validate_domain(payload.domain).normalized

    # 2. Decide LLM mode
    settings: Settings = request.app.state.settings
    daily_counter = request.app.state.daily_llm_counter
    if daily_counter.try_increment():
        graph = request.app.state.graph
        narrative_source = "gemini"
    else:
        null_supervisor = SupervisorAgent(explainer=NullExplainer())
        graph = build_investigation_graph(supervisor=null_supervisor)
        narrative_source = "deterministic_only"

    # 3. Run graph with timeout
    timeout = getattr(request.app.state, "investigation_timeout", 60.0)
    final_state = await asyncio.wait_for(
        graph.ainvoke({"domain": payload.domain}),
        timeout=timeout,
    )
    assessment: SupervisorAssessment | None = final_state.get("assessment")
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Investigation pipeline did not produce an assessment",
        )

    # 4. Build response body
    share_id = uuid.uuid4()
    created_at = datetime.now(UTC)
    result_data = {
        "share_id": str(share_id),
        "domain": payload.domain,
        "normalized_domain": norm_domain,
        "created_at": created_at.isoformat(),
        "assessment": assessment.model_dump(mode="json"),
        "narrative_source": narrative_source,
    }

    # 5. Persist via PublicResultRepository
    repo = PublicResultRepository(session)
    await repo.create(
        domain=payload.domain,
        normalized_domain=norm_domain,
        result=result_data,
        ttl_seconds=settings.public_result_ttl_seconds,
    )
    await session.commit()

    # 6. Return 201
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=result_data)


@router.get("/r/{share_id}")
async def get_public_result(
    share_id: uuid.UUID,
    request: Request,
    _: Annotated[None, Depends(check_public_rate_limit)] = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,  # type: ignore[assignment]
) -> JSONResponse:
    """Fetch a shared result. 404 if expired or missing. Same shape as POST response."""
    repo = PublicResultRepository(session)
    item = await repo.get(share_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared result not found or has expired",
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=item.result)
