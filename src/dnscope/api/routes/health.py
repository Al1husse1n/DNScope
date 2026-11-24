from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from dnscope.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse | JSONResponse:
    """Check DB connectivity with SELECT 1.

    If it fails: return JSONResponse(status_code=503, content={"status":
    "degraded", "db": "unreachable"}). Else return {"status": "ok", "db":
    "ok"}.
    """
    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            await session.execute(text("SELECT 1;"))
        return HealthResponse(status="ok", db="ok")
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unreachable"},
        )
