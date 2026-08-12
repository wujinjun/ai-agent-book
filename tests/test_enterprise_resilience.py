from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_agent_book.apps.enterprise_platform import (
    EnterprisePlatform,
    HMACIdentityVerifier,
    Principal,
    RunExecutionContext,
    RunRecord,
    create_enterprise_app,
    replay_approvals,
    runs,
    schema_versions,
)


class SwitchableExecutor:
    def __init__(self) -> None:
        self.fail = True

    def __call__(self, run: RunRecord, docs: list[dict[str, str]]) -> str:
        if self.fail:
            raise TimeoutError(f"provider failure for sensitive prompt: {run.prompt}")
        return f"recovered:{len(docs)}"


def _platform(
    path: Path,
    *,
    executor: SwitchableExecutor | None = None,
    max_attempts: int = 3,
) -> tuple[EnterprisePlatform, str]:
    platform = EnterprisePlatform(
        path,
        run_executor=executor,
        max_attempts=max_attempts,
    )
    platform.create_tenant("tenant-a", "Tenant A")
    platform.create_tenant("tenant-b", "Tenant B")
    platform.create_user("tenant-a", "admin-a", role="admin")
    platform.create_user("tenant-a", "member-a", role="member")
    platform.create_user("tenant-a", "member-b", role="member")
    platform.create_user("tenant-b", "admin-b", role="admin")
    agent = platform.register_agent("tenant-a", "admin-a", "assistant", "assistant")
    session = platform.create_session("tenant-a", "member-a", agent.agent_id)
    return platform, session.session_id


def test_failures_retry_then_enter_tenant_scoped_dead_letter_queue(tmp_path: Path) -> None:
    executor = SwitchableExecutor()
    platform, session_id = _platform(
        tmp_path / "platform.db", executor=executor, max_attempts=2
    )
    run = platform.submit_run("tenant-a", "member-a", session_id, "private prompt")
    first = platform.process_next()
    second = platform.process_next()
    assert first is not None and first.status == "queued"
    assert second is not None and second.status == "failed"
    letters = platform.list_dead_letters("tenant-a", "admin-a")
    assert letters[0].run_id == run.run_id
    assert letters[0].attempts == 2
    assert letters[0].error_type == "TimeoutError"
    assert platform.list_dead_letters("tenant-b", "admin-b") == []
    assert "private prompt" not in letters[0].model_dump_json()


def test_admin_can_retry_dead_letter_after_provider_recovers(tmp_path: Path) -> None:
    executor = SwitchableExecutor()
    platform, session_id = _platform(
        tmp_path / "platform.db", executor=executor, max_attempts=1
    )
    run = platform.submit_run("tenant-a", "member-a", session_id, "task")
    platform.process_next()
    executor.fail = False
    _, token = platform.approve_dead_letter_replay("tenant-a", "admin-a", run.run_id)
    queued = platform.retry_dead_letter(
        "tenant-a", "admin-a", run.run_id, approval_token=token
    )
    completed = platform.process_next()
    assert queued.status == "queued"
    assert completed is not None and completed.status == "succeeded"
    assert platform.list_dead_letters("tenant-a", "admin-a") == []


def test_member_can_cancel_only_owned_queued_run(tmp_path: Path) -> None:
    platform, session_id = _platform(tmp_path / "platform.db")
    run = platform.submit_run("tenant-a", "member-a", session_id, "task")
    with pytest.raises(PermissionError):
        platform.cancel_run("tenant-a", "member-b", run.run_id)
    cancelled = platform.cancel_run("tenant-a", "member-a", run.run_id)
    assert cancelled.status == "cancelled"
    assert platform.get_run("tenant-a", run.run_id).status == "cancelled"


def test_sqlite_backup_is_consistent_and_reopenable(tmp_path: Path) -> None:
    platform, session_id = _platform(tmp_path / "platform.db")
    run = platform.submit_run("tenant-a", "member-a", session_id, "persist")
    platform.process_next()
    backup = platform.backup_sqlite(tmp_path / "backups" / "platform.db")
    restored = EnterprisePlatform(backup)
    assert restored.get_run("tenant-a", run.run_id).status == "succeeded"
    assert restored.list_traces("tenant-a", run.run_id)


def test_signed_identity_adapter_rejects_headers_tampering_and_expiry(tmp_path: Path) -> None:
    platform, _ = _platform(tmp_path / "platform.db")
    verifier = HMACIdentityVerifier("a-local-test-secret-with-at-least-32-bytes")
    client = TestClient(create_enterprise_app(platform, identity_verifier=verifier))
    token = verifier.issue(Principal(tenant_id="tenant-a", user_id="admin-a"))
    allowed = client.get("/admin/runs", headers={"Authorization": f"Bearer {token}"})
    assert allowed.status_code == 200
    assert client.get(
        "/admin/runs", headers={"X-Tenant-ID": "tenant-a", "X-User-ID": "admin-a"}
    ).status_code == 401
    assert client.get(
        "/admin/runs", headers={"Authorization": f"Bearer {token}x"}
    ).status_code == 401
    expired = verifier.issue(
        Principal(tenant_id="tenant-a", user_id="admin-a"), ttl_seconds=-1
    )
    assert client.get(
        "/admin/runs", headers={"Authorization": f"Bearer {expired}"}
    ).status_code == 401


def test_dead_letter_admin_api_is_rbac_protected(tmp_path: Path) -> None:
    executor = SwitchableExecutor()
    platform, session_id = _platform(
        tmp_path / "platform.db", executor=executor, max_attempts=1
    )
    platform.submit_run("tenant-a", "member-a", session_id, "task")
    platform.process_next()
    client = TestClient(create_enterprise_app(platform))
    admin = {"X-Tenant-ID": "tenant-a", "X-User-ID": "admin-a"}
    member = {"X-Tenant-ID": "tenant-a", "X-User-ID": "member-a"}
    assert client.get("/admin/dead-letters", headers=admin).status_code == 200
    assert client.get("/admin/dead-letters", headers=member).status_code == 403


def test_dead_letter_http_replay_requires_fresh_approval_token(tmp_path: Path) -> None:
    executor = SwitchableExecutor()
    platform, session_id = _platform(
        tmp_path / "platform.db", executor=executor, max_attempts=1
    )
    run = platform.submit_run("tenant-a", "member-a", session_id, "task")
    platform.process_next()
    client = TestClient(create_enterprise_app(platform))
    admin = {"X-Tenant-ID": "tenant-a", "X-User-ID": "admin-a"}

    rejected = client.post(
        f"/admin/dead-letters/{run.run_id}/retry",
        headers=admin,
        json={"approval_token": "0" * 64},
    )
    approval = client.post(
        f"/admin/dead-letters/{run.run_id}/approval",
        headers=admin,
        json={"ttl_seconds": 30},
    )
    accepted = client.post(
        f"/admin/dead-letters/{run.run_id}/retry",
        headers=admin,
        json={"approval_token": approval.json()["token"]},
    )

    assert rejected.status_code == 403
    assert approval.status_code == 200
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "queued"


def test_trace_evaluation_readiness_and_metrics_are_exposed(tmp_path: Path) -> None:
    platform, session_id = _platform(tmp_path / "platform.db")
    run = platform.submit_run("tenant-a", "member-a", session_id, "task")
    platform.process_next()
    client = TestClient(create_enterprise_app(platform))
    admin = {"X-Tenant-ID": "tenant-a", "X-User-ID": "admin-a"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    assert client.get(f"/runs/{run.run_id}/traces", headers=admin).json()
    evaluation = client.post(f"/admin/runs/{run.run_id}/evaluations", headers=admin)
    assert evaluation.json()["passed"] is True
    metrics = client.get("/metrics", headers=admin)
    assert "agent_platform_runs" in metrics.text


def test_worker_api_never_processes_or_returns_another_tenants_run(tmp_path: Path) -> None:
    platform, _ = _platform(tmp_path / "platform.db")
    agent_b = platform.register_agent("tenant-b", "admin-b", "assistant-b", "assistant")
    session_b = platform.create_session("tenant-b", "admin-b", agent_b.agent_id)
    run_b = platform.submit_run("tenant-b", "admin-b", session_b.session_id, "tenant b task")
    client = TestClient(create_enterprise_app(platform))

    tenant_a = {"X-Tenant-ID": "tenant-a", "X-User-ID": "admin-a"}
    tenant_b = {"X-Tenant-ID": "tenant-b", "X-User-ID": "admin-b"}
    assert client.post("/worker/process-one", headers=tenant_a).json() is None
    processed = client.post("/worker/process-one", headers=tenant_b)

    assert processed.status_code == 200
    assert processed.json()["run_id"] == run_b.run_id


def test_expired_running_lease_is_recovered_after_worker_crash(tmp_path: Path) -> None:
    platform, session_id = _platform(tmp_path / "platform.db")
    run = platform.submit_run("tenant-a", "member-a", session_id, "recover")
    with platform.engine.begin() as connection:
        connection.execute(
            runs.update()
            .where(runs.c.run_id == run.run_id)
            .values(
                status="running",
                worker_id="crashed-worker",
                lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )

    recovered = platform.process_next(tenant_id="tenant-a")

    assert recovered is not None and recovered.status == "succeeded"


def test_resilience_schema_version_is_recorded(tmp_path: Path) -> None:
    platform, _ = _platform(tmp_path / "platform.db")
    with platform.engine.connect() as connection:
        versions = connection.execute(schema_versions.select()).scalars().all()
    assert versions == [1, 2, 3]


def test_running_executor_observes_cooperative_cancellation(tmp_path: Path) -> None:
    platform: EnterprisePlatform

    def executor(
        run: RunRecord, docs: list[dict[str, str]], context: RunExecutionContext
    ) -> str:
        platform.cancel_run(run.tenant_id, "member-a", run.run_id)
        context.checkpoint()
        return "must not be committed"

    platform, session_id = _platform(tmp_path / "platform.db")
    platform.run_executor = executor
    run = platform.submit_run("tenant-a", "member-a", session_id, "cancel me")

    result = platform.process_next(tenant_id="tenant-a")

    assert result is not None and result.status == "cancelled"
    assert platform.get_run("tenant-a", run.run_id).output == "cancelled"
    assert [trace.event for trace in platform.list_traces("tenant-a", run.run_id)][-2:] == [
        "run.cancel_requested",
        "run.cancelled",
    ]


def test_only_current_worker_can_renew_lease(tmp_path: Path) -> None:
    platform, session_id = _platform(tmp_path / "platform.db")
    run = platform.submit_run("tenant-a", "member-a", session_id, "long task")
    with platform.engine.begin() as connection:
        connection.execute(
            runs.update()
            .where(runs.c.run_id == run.run_id)
            .values(status="running", worker_id="worker-current")
        )

    expires_at = platform.heartbeat_run(run.run_id, "worker-current")

    assert expires_at > datetime.now(UTC)
    with pytest.raises(RuntimeError, match="cannot be renewed"):
        platform.heartbeat_run(run.run_id, "worker-stale")


def test_dead_letter_replay_approval_is_content_bound_and_single_use(tmp_path: Path) -> None:
    executor = SwitchableExecutor()
    platform, session_id = _platform(
        tmp_path / "platform.db", executor=executor, max_attempts=1
    )
    first = platform.submit_run("tenant-a", "member-a", session_id, "first")
    platform.process_next()
    approval, token = platform.approve_dead_letter_replay(
        "tenant-a", "admin-a", first.run_id
    )
    assert approval.content_hash
    queued = platform.retry_dead_letter(
        "tenant-a", "admin-a", first.run_id, approval_token=token
    )
    assert queued.status == "queued"
    with pytest.raises((KeyError, PermissionError)):
        platform.retry_dead_letter(
            "tenant-a", "admin-a", first.run_id, approval_token=token
        )

    second = platform.submit_run("tenant-a", "member-a", session_id, "second")
    platform.process_next()
    platform.process_next()
    _, second_token = platform.approve_dead_letter_replay(
        "tenant-a", "admin-a", second.run_id
    )
    with platform.engine.begin() as connection:
        connection.execute(
            runs.update().where(runs.c.run_id == second.run_id).values(prompt="changed")
        )
    with pytest.raises(PermissionError, match="content-bound"):
        platform.retry_dead_letter(
            "tenant-a", "admin-a", second.run_id, approval_token=second_token
        )


def test_expired_dead_letter_replay_approval_is_rejected(tmp_path: Path) -> None:
    executor = SwitchableExecutor()
    platform, session_id = _platform(
        tmp_path / "platform.db", executor=executor, max_attempts=1
    )
    run = platform.submit_run("tenant-a", "member-a", session_id, "expired")
    platform.process_next()
    _, token = platform.approve_dead_letter_replay("tenant-a", "admin-a", run.run_id)
    with platform.engine.begin() as connection:
        connection.execute(
            replay_approvals.update().values(
                expires_at=datetime.now(UTC) - timedelta(seconds=1)
            )
        )

    with pytest.raises(PermissionError, match="content-bound"):
        platform.retry_dead_letter(
            "tenant-a", "admin-a", run.run_id, approval_token=token
        )
