import asyncio
import time
from datetime import UTC
from typing import Any
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.testclient import TestClient

from dnscope.api.main import app
from dnscope.db.repository import ApiKeyRepository, InvestigationJobRepository
from dnscope.db.session import build_session_factory
from dnscope.jobs.runner import JobRunner
from dnscope.schemas.common import AgentStatus, RiskLevel
from dnscope.schemas.findings import DNSFinding, RegistrationFinding, ReputationFinding
from dnscope.schemas.scoring import RuleHit, ScoreResult
from dnscope.schemas.supervisor import SupervisorAssessment


class FakeGraph:
    def __init__(
        self,
        canned_state: dict[str, Any] | None = None,
        should_raise: bool = False,
        sleep_seconds: float = 0.0,
    ) -> None:
        self.canned_state = canned_state or {}
        self.should_raise = should_raise
        self.sleep_seconds = sleep_seconds
        self.call_count = 0

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        if self.sleep_seconds > 0:
            await asyncio.sleep(self.sleep_seconds)
        if self.should_raise:
            raise RuntimeError("Fake graph computation error")
        return self.canned_state


def make_canned_assessment(score: int = 30) -> SupervisorAssessment:
    return SupervisorAssessment(
        score_result=ScoreResult(
            score=score,
            risk_level=RiskLevel.LOW,
            rule_hits=[
                RuleHit(
                    rule_id="RULE_TEST",
                    description="Test description",
                    points=score,
                    evidence_refs=[],
                )
            ],
            total_points_before_clamp=score,
        ),
        rule_trace_explanation="Rule trace explanation",
        narrative="Test narrative string",
        inconclusive_checks=[],
    )


def make_canned_state(domain: str = "example.com", score: int = 30) -> dict[str, Any]:
    return {
        "domain": domain,
        "dns": DNSFinding(status=AgentStatus.OK, a_records=["1.2.3.4"]),
        "registration": RegistrationFinding(status=AgentStatus.OK, registrar="Safe Registrar"),
        "reputation": ReputationFinding(status=AgentStatus.OK, detections_malicious=0),
        "assessment": make_canned_assessment(score),
    }


# 1. POST /investigations (default, no sync) -> 202 with job_id, status: PENDING
def test_create_job_default_async(user_client: TestClient) -> None:
    fake_graph = FakeGraph(canned_state=make_canned_state("jobs1.com"), sleep_seconds=0.1)
    app.state.graph = fake_graph
    app.state.job_runner = JobRunner(fake_graph, app.state.session_factory)

    res = user_client.post("/investigations", json={"domain": "jobs1.com"})
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "PENDING"


# 2 & 3. Poll GET /jobs/{id} -> COMPLETED with investigation_id set, fetchable at GET /investigations/{id}
def test_job_completion_and_fetchable(user_client: TestClient) -> None:
    fake_graph = FakeGraph(canned_state=make_canned_state("jobs2.com", score=40))
    app.state.graph = fake_graph
    app.state.job_runner = JobRunner(fake_graph, app.state.session_factory)

    res = user_client.post("/investigations", json={"domain": "jobs2.com"})
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # Poll until COMPLETED
    start = time.monotonic()
    job_data = None
    while time.monotonic() - start < 5.0:
        poll_res = user_client.get(f"/jobs/{job_id}")
        assert poll_res.status_code == 200
        job_data = poll_res.json()
        if job_data["status"] == "COMPLETED":
            break
        time.sleep(0.05)

    assert job_data is not None
    assert job_data["status"] == "COMPLETED"
    assert job_data["investigation_id"] is not None

    # Fetch investigation
    inv_id = job_data["investigation_id"]
    inv_res = user_client.get(f"/investigations/{inv_id}")
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["id"] == inv_id
    assert inv_data["domain"] == "jobs2.com"
    assert inv_data["assessment"]["score_result"]["score"] == 40


# 4. Job with domain that fails validation -> 400 at enqueue time (job is never created)
def test_job_invalid_domain_never_created(user_client: TestClient) -> None:
    fake_graph = FakeGraph(canned_state=make_canned_state())
    app.state.graph = fake_graph
    app.state.job_runner = JobRunner(fake_graph, app.state.session_factory)

    res = user_client.post("/investigations", json={"domain": "http://invalid-domain"})
    assert res.status_code == 400
    assert res.json().get("error") == "invalid_domain"
    assert fake_graph.call_count == 0


# 5. Fake graph that raises -> job FAILED, error populated, investigation_id null
def test_job_graph_failure_marks_failed(user_client: TestClient) -> None:
    failing_graph = FakeGraph(should_raise=True)
    app.state.graph = failing_graph
    app.state.job_runner = JobRunner(failing_graph, app.state.session_factory)

    res = user_client.post("/investigations", json={"domain": "failing-job.com"})
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    start = time.monotonic()
    job_data = None
    while time.monotonic() - start < 5.0:
        poll_res = user_client.get(f"/jobs/{job_id}")
        assert poll_res.status_code == 200
        job_data = poll_res.json()
        if job_data["status"] == "FAILED":
            break
        time.sleep(0.05)

    assert job_data is not None
    assert job_data["status"] == "FAILED"
    assert job_data["investigation_id"] is None
    assert job_data["error"] is not None
    assert "Fake graph computation error" in job_data["error"]


# 6. Background task uses its own session (spy on session_factory)
def test_background_task_uses_own_session(user_client: TestClient) -> None:
    real_session_factory = app.state.session_factory
    spy_factory = MagicMock(side_effect=real_session_factory)

    fake_graph = FakeGraph(canned_state=make_canned_state("own-session.com"))
    runner = JobRunner(fake_graph, spy_factory)
    app.state.job_runner = runner

    res = user_client.post("/investigations", json={"domain": "own-session.com"})
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    start = time.monotonic()
    while time.monotonic() - start < 5.0:
        poll = user_client.get(f"/jobs/{job_id}")
        if poll.json()["status"] == "COMPLETED":
            break
        time.sleep(0.05)

    # JobRunner must have called session_factory independently for the job task
    assert spy_factory.call_count >= 1


# 7. Shutdown awaits tasks: send 3 jobs, immediately call await_all, assert all complete/fail without warning
def test_shutdown_awaits_tasks(user_client: TestClient) -> None:
    fake_graph = FakeGraph(canned_state=make_canned_state("shutdown.com"), sleep_seconds=0.1)
    runner = JobRunner(fake_graph, app.state.session_factory)
    app.state.job_runner = runner

    job_ids = []
    for i in range(3):
        res = user_client.post("/investigations", json={"domain": f"shutdown{i}.com"})
        assert res.status_code == 202
        job_ids.append(res.json()["job_id"])

    # Await all running tasks
    if hasattr(user_client, "portal") and user_client.portal is not None:
        user_client.portal.call(runner.await_all, 5.0)
    else:
        asyncio.run(runner.await_all(timeout=5.0))

    # All jobs must now be COMPLETED
    for jid in job_ids:
        poll = user_client.get(f"/jobs/{jid}")
        assert poll.json()["status"] == "COMPLETED"


# 8. Stale job recovery marks PENDING/RUNNING jobs older than cutoff as FAILED
def test_recover_stale_jobs_marks_stale_failed(db_engine: AsyncEngine) -> None:
    import uuid
    from datetime import datetime, timedelta

    from dnscope.jobs.recovery import recover_stale_jobs

    async def _test() -> None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            key_repo = ApiKeyRepository(session)
            k = await key_repo.create(
                name="recovery-test",
                key_hash=f"hash_{uuid.uuid4()}",
                hmac_prefix="prefix1234567890",
                role="user",
            )
            job_repo = InvestigationJobRepository(session)
            stale_job = await job_repo.create(
                api_key_id=k.id,
                domain="stale.com",
                status="RUNNING",
            )
            # Manually backdate updated_at
            stale_job.updated_at = datetime.now(UTC) - timedelta(seconds=600)
            await session.commit()

            recovered = await recover_stale_jobs(session, stale_seconds=300)
            assert recovered >= 1

            reloaded = await job_repo.get(stale_job.id)
            assert reloaded is not None
            assert reloaded.status == "FAILED"
            assert reloaded.error == "process restarted before completion"

    asyncio.run(_test())


# 9. Stale job recovery ignores recent RUNNING jobs
def test_recover_stale_jobs_ignores_recent_jobs(db_engine: AsyncEngine) -> None:
    import uuid

    from dnscope.jobs.recovery import recover_stale_jobs

    async def _test() -> None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            key_repo = ApiKeyRepository(session)
            k = await key_repo.create(
                name="recovery-test2",
                key_hash=f"hash_{uuid.uuid4()}",
                hmac_prefix="prefix1234567891",
                role="user",
            )
            job_repo = InvestigationJobRepository(session)
            recent_job = await job_repo.create(
                api_key_id=k.id,
                domain="recent.com",
                status="RUNNING",
            )
            await session.commit()

            recovered = await recover_stale_jobs(session, stale_seconds=300)
            assert recovered == 0
            reloaded = await job_repo.get(recent_job.id)
            assert reloaded is not None
            assert reloaded.status == "RUNNING"

    asyncio.run(_test())


# 10. Stale job recovery ignores already COMPLETED jobs
def test_recover_stale_jobs_ignores_completed_jobs(db_engine: AsyncEngine) -> None:
    import uuid
    from datetime import datetime, timedelta

    from dnscope.jobs.recovery import recover_stale_jobs

    async def _test() -> None:
        factory = build_session_factory(db_engine)
        async with factory() as session:
            key_repo = ApiKeyRepository(session)
            k = await key_repo.create(
                name="recovery-test3",
                key_hash=f"hash_{uuid.uuid4()}",
                hmac_prefix="prefix1234567892",
                role="user",
            )
            job_repo = InvestigationJobRepository(session)
            done_job = await job_repo.create(
                api_key_id=k.id,
                domain="done.com",
                status="COMPLETED",
            )
            done_job.updated_at = datetime.now(UTC) - timedelta(seconds=600)
            await session.commit()

            recovered = await recover_stale_jobs(session, stale_seconds=300)
            assert recovered == 0
            reloaded = await job_repo.get(done_job.id)
            assert reloaded is not None
            assert reloaded.status == "COMPLETED"

    asyncio.run(_test())


# 11. Job runner empty tasks await_all returns quickly
def test_job_runner_empty_tasks_await_all() -> None:
    fake_graph = FakeGraph(canned_state=make_canned_state())
    runner = JobRunner(fake_graph, app.state.session_factory)
    asyncio.run(runner.await_all(timeout=1.0))
