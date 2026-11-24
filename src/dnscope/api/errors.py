from fastapi import Request
from fastapi.responses import JSONResponse

from dnscope.auth.models import AuthError


async def domain_validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return 400 with {"error": "invalid_domain", "detail": str(exc),
    "request_id": request.state.request_id}."""
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_domain",
            "detail": str(exc),
            "request_id": request_id,
        },
    )


async def investigation_timeout_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return 504 with {"error": "investigation_timeout", ...}."""
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=504,
        content={
            "error": "investigation_timeout",
            "detail": str(exc),
            "request_id": request_id,
        },
    )


async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Return custom JSON for auth errors matching tests contract."""
    response = JSONResponse(status_code=exc.status_code, content={"error": exc.error})
    request_id = getattr(request.state, "request_id", "")
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response
