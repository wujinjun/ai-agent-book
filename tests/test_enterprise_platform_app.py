from pathlib import Path

import httpx
import pytest

from ai_agent_book.apps.enterprise_platform import EnterprisePlatform, create_enterprise_app


class FailingQueue:
    def push(self, run_id: str) -> None:
        raise ConnectionError("redis unavailable")

    def pop(self) -> str | None:
        raise ConnectionError("redis unavailable")


def _platform(tmp_path: Path) -> EnterprisePlatform:
    platform = EnterprisePlatform(tmp_path / "platform.db")
    platform.create_tenant("tenant-a", "Tenant A")
    platform.create_tenant("tenant-b", "Tenant B")
    platform.create_user("tenant-a", "admin-a", role="admin")
    platform.create_user("tenant-a", "member-a", role="member")
    platform.create_user("tenant-b", "admin-b", role="admin")
    return platform


def test_platform_registers_everything_and_evaluates(tmp_path: Path) -> None:
    platform = _platform(tmp_path)
    agent = platform.register_agent("tenant-a", "admin-a", "knowledge", "rag")
    tool = platform.register_tool(
        "tenant-a", "admin-a", "local-mcp", kind="mcp", endpoint="stdio://local"
    )
    session = platform.create_session("tenant-a", "member-a", agent.agent_id)
    platform.add_document("tenant-a", "policy", "请假制度允许员工提前申请。")
    platform.submit_run("tenant-a", "member-a", session.session_id, "请假制度是什么？")

    completed = platform.process_next()

    assert tool.kind == "mcp"
    assert completed is not None and completed.status == "succeeded"
    assert "请假制度" in completed.output
    assert platform.list_traces("tenant-a", completed.run_id)
    evaluation = platform.evaluate_run("tenant-a", "admin-a", completed.run_id)
    assert evaluation.passed is True


def test_permissions_and_tenant_isolation_are_enforced(tmp_path: Path) -> None:
    platform = _platform(tmp_path)
    with pytest.raises(PermissionError):
        platform.register_agent("tenant-a", "member-a", "forbidden", "assistant")
    agent = platform.register_agent("tenant-a", "admin-a", "a", "assistant")
    session = platform.create_session("tenant-a", "member-a", agent.agent_id)
    run = platform.submit_run("tenant-a", "member-a", session.session_id, "hello")
    with pytest.raises(PermissionError):
        platform.get_run("tenant-b", run.run_id)


def test_database_queue_recovers_when_redis_wakeup_is_unavailable(tmp_path: Path) -> None:
    platform = EnterprisePlatform(tmp_path / "fallback.db", queue=FailingQueue())
    platform.create_tenant("t", "T")
    platform.create_user("t", "admin", role="admin")
    agent = platform.register_agent("t", "admin", "assistant", "assistant")
    session = platform.create_session("t", "admin", agent.agent_id)
    submitted = platform.submit_run("t", "admin", session.session_id, "hello")
    completed = platform.process_next()
    assert completed is not None
    assert completed.run_id == submitted.run_id
    assert completed.status == "succeeded"


def test_bootstrap_ensure_methods_are_idempotent(tmp_path: Path) -> None:
    platform = EnterprisePlatform(tmp_path / "bootstrap.db")
    platform.ensure_tenant("demo", "Demo")
    platform.ensure_tenant("demo", "Demo")
    platform.ensure_user("demo", "admin", role="admin")
    platform.ensure_user("demo", "admin", role="admin")
    assert platform.list_runs("demo", "admin") == []


@pytest.mark.asyncio
async def test_admin_api_requires_tenant_and_user_headers(tmp_path: Path) -> None:
    platform = _platform(tmp_path)
    app = create_enterprise_app(platform)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unauthorized = await client.get("/admin/runs")
        allowed = await client.get(
            "/admin/runs",
            headers={"X-Tenant-ID": "tenant-a", "X-User-ID": "admin-a"},
        )
        forbidden = await client.get(
            "/admin/runs",
            headers={"X-Tenant-ID": "tenant-a", "X-User-ID": "member-a"},
        )
    assert unauthorized.status_code == 422
    assert allowed.status_code == 200
    assert forbidden.status_code == 403
