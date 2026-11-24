import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dnscope.db.repository import InvestigationJobRepository, InvestigationRepository
from dnscope.validation import validate_domain


class JobRunner:
    """In-process background task runner.

    Responsibilities:
      - Start a job: creates PENDING row (caller does this), then spawns
        asyncio.create_task() executing the actual graph.
      - On completion: updates row to COMPLETED, writes investigation_id,
        persists investigation with the api_key_id from the job.
      - On exception: updates row to FAILED with error = repr(exc) truncated to 1024 chars.
      - Tracks tasks in self._tasks: dict[UUID, asyncio.Task] so they can be awaited on shutdown.
      - Exposes async def await_all(self, timeout: float = 30.0).
    """

    def __init__(
        self,
        graph: Any,
        session_factory: async_sessionmaker[AsyncSession],
        logger: logging.Logger | None = None,
    ) -> None:
        self.graph = graph
        self.session_factory = session_factory
        self.logger = logger or logging.getLogger("dnscope.jobs.runner")
        self._tasks: dict[UUID, asyncio.Task[Any]] = {}

    async def start(
        self,
        job_id: UUID,
        domain: str,
        api_key_id: UUID,
    ) -> None:
        """Spawn the background task and return immediately."""
        task = asyncio.create_task(self._run_job(job_id, domain, api_key_id))
        self._tasks[job_id] = task

        def _cleanup(_: asyncio.Task[Any]) -> None:
            self._tasks.pop(job_id, None)

        task.add_done_callback(_cleanup)

    async def _run_job(
        self,
        job_id: UUID,
        domain: str,
        api_key_id: UUID,
    ) -> None:
        """Execute the investigation graph using a dedicated AsyncSession."""
        async with self.session_factory() as session:
            job_repo = InvestigationJobRepository(session)
            inv_repo = InvestigationRepository(session)

            # Mark RUNNING
            await job_repo.update_status(job_id, status="RUNNING")
            await session.commit()

            try:
                state = {"domain": domain}
                result_state = await self.graph.ainvoke(state)
                assessment = result_state.get("assessment")
                if assessment is None:
                    raise ValueError("Graph error: assessment was None")

                validated = validate_domain(domain)
                normalized_domain = validated.normalized

                findings_dict = {
                    "dns": (
                        result_state.get("dns").model_dump(mode="json")
                        if result_state.get("dns")
                        else None
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

                inv = await inv_repo.create(
                    domain=domain,
                    normalized_domain=normalized_domain,
                    findings=findings_dict,
                    assessment=assessment,
                    api_key_id=api_key_id,
                )

                await job_repo.update_status(
                    job_id,
                    status="COMPLETED",
                    investigation_id=inv.id,
                )
                await session.commit()
            except Exception as exc:
                err_msg = repr(exc)[:1024]
                self.logger.error("Job %s failed: %s", job_id, err_msg)
                try:
                    await job_repo.update_status(
                        job_id,
                        status="FAILED",
                        error=err_msg,
                    )
                    await session.commit()
                except Exception as commit_exc:
                    self.logger.error("Failed to commit job failure state: %s", commit_exc)

    async def await_all(self, timeout: float = 30.0) -> None:
        """Wait for all running tasks to finish during graceful shutdown or tests."""
        tasks = list(self._tasks.values())
        if not tasks:
            return
        _done, pending = await asyncio.wait(tasks, timeout=timeout)
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
