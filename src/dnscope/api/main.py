from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from dnscope.api.errors import (
    domain_validation_error_handler,
    investigation_timeout_handler,
)
from dnscope.api.middleware import RequestContextMiddleware
from dnscope.api.routes import health, investigations
from dnscope.config import Settings
from dnscope.db.session import build_engine, build_session_factory
from dnscope.factory import build_supervisor
from dnscope.graph.workflow import build_investigation_graph
from dnscope.logging_setup import configure_logging
from dnscope.validation import DomainValidationError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """On startup:
      - configure_logging(Settings())
      - engine = build_engine(settings.database_url)
      - app.state.session_factory = build_session_factory(engine)
      - supervisor = build_supervisor(settings)
      - app.state.graph = build_investigation_graph(supervisor=supervisor)
    On shutdown:
      - await engine.dispose()
    """
    settings = Settings()
    configure_logging(settings)
    engine = build_engine(settings.database_url)
    app.state.session_factory = build_session_factory(engine)
    supervisor = build_supervisor(settings)
    app.state.graph = build_investigation_graph(supervisor=supervisor)
    app.state.investigation_timeout = 60.0
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="dnscope", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(DomainValidationError, domain_validation_error_handler)
    app.add_exception_handler(TimeoutError, investigation_timeout_handler)
    app.include_router(health.router)
    app.include_router(investigations.router)
    return app


app = create_app()
