import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("dnscope.api.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """On each request:

    1. Generate request_id = str(uuid.uuid4()).
    2. Attach to request.state.request_id.
    3. Set response header X-Request-ID.
    4. Time the request.
    5. Emit a single structured log line via logger 'dnscope.api.access' with:
       request_id, method, path, status, duration_ms.
    6. On exception, log at ERROR with the same fields plus error_type,
       then re-raise (FastAPI's exception handler takes over).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                },
            )
            raise
