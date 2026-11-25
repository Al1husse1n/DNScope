import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dnscope.api.daily_counter import DailyCounter
from dnscope.api.errors import (
    auth_error_handler,
    domain_validation_error_handler,
    investigation_timeout_handler,
)
from dnscope.api.middleware import RequestContextMiddleware
from dnscope.api.routes import admin, health, investigations, jobs, public
from dnscope.auth.models import AuthError
from dnscope.auth.rate_limit import InMemoryRateLimiter
from dnscope.config import Settings
from dnscope.db.public_repository import PublicResultRepository
from dnscope.db.session import build_engine, build_session_factory
from dnscope.factory import build_supervisor
from dnscope.graph.workflow import build_investigation_graph
from dnscope.jobs.recovery import recover_stale_jobs
from dnscope.jobs.runner import JobRunner
from dnscope.logging_setup import configure_logging
from dnscope.validation import DomainValidationError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """On startup:
      - configure_logging(Settings())
      - engine = build_engine(settings.database_url)
      - app.state.session_factory = build_session_factory(engine)
      - run recovery sweep: await recover_stale_jobs(...)
      - supervisor = build_supervisor(settings)
      - app.state.graph = build_investigation_graph(supervisor=supervisor)
      - app.state.rate_limiter = InMemoryRateLimiter(settings.rate_limit_per_minute)
      - app.state.job_runner = JobRunner(app.state.graph, app.state.session_factory)
    On shutdown:
      - await job_runner.await_all(timeout=30.0)
      - await engine.dispose()
    """
    settings = Settings()
    configure_logging(settings)
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    # Startup recovery sweep
    async with session_factory() as session:
        await recover_stale_jobs(session, stale_seconds=settings.job_recovery_stale_seconds)

    supervisor = build_supervisor(settings)
    app.state.graph = build_investigation_graph(supervisor=supervisor)
    app.state.investigation_timeout = 60.0
    app.state.rate_limiter = InMemoryRateLimiter(settings.rate_limit_per_minute)
    app.state.public_limiter = InMemoryRateLimiter(
        limit_per_minute=settings.public_rate_limit_per_hour,
        window_seconds=3600.0,
    )
    app.state.daily_llm_counter = DailyCounter(cap=settings.public_llm_daily_cap)
    app.state.job_runner = JobRunner(app.state.graph, session_factory)

    async def cleanup_loop() -> None:
        while True:
            try:
                await asyncio.sleep(600)
                async with session_factory() as session:
                    repo = PublicResultRepository(session)
                    await repo.delete_expired()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Background cleanup task failed: %s", exc)

    cleanup_task = asyncio.create_task(cleanup_loop())

    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        await app.state.job_runner.await_all(timeout=30.0)
        await engine.dispose()


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(title="dnscope", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,  # we use X-API-Key header, not cookies
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(DomainValidationError, domain_validation_error_handler)
    app.add_exception_handler(TimeoutError, investigation_timeout_handler)
    app.add_exception_handler(AuthError, auth_error_handler)  # type: ignore[arg-type]
    app.include_router(health.router)
    app.include_router(investigations.router)
    app.include_router(jobs.router)
    app.include_router(admin.router)
    app.include_router(public.router)
    return app


app = create_app()
