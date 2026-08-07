from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_agent_book.project_service import ServiceSettings, create_project_app

HEADERS = {
    "X-Tenant-ID": "tenant-a",
    "X-User-ID": "user-a",
    "X-Roles": "project:run,project:observe",
}


@pytest.fixture(params=range(1, 11))
def client(request: pytest.FixtureRequest, tmp_path: Path) -> TestClient:
    settings = ServiceSettings(database_path=tmp_path / f"project-{request.param}.db")
    return TestClient(create_project_app(request.param, settings=settings))


def test_all_projects_expose_health_and_durable_run_contract(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200
    response = client.post(
        "/v1/runs",
        headers={**HEADERS, "Idempotency-Key": "run-1"},
        json={"prompt": "验证生产服务边界"},
    )
    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "succeeded"
    assert client.get(f"/v1/runs/{run['run_id']}", headers=HEADERS).json() == run
    events = client.get(f"/v1/runs/{run['run_id']}/events", headers=HEADERS)
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "event: succeeded" in events.text
    assert "agent_project_audit_events" in client.get("/metrics", headers=HEADERS).text


def test_idempotency_replays_same_run_and_rejects_payload_change(client: TestClient) -> None:
    headers = {**HEADERS, "Idempotency-Key": "stable-key"}
    first = client.post("/v1/runs", headers=headers, json={"prompt": "same"})
    replay = client.post("/v1/runs", headers=headers, json={"prompt": "same"})
    conflict = client.post("/v1/runs", headers=headers, json={"prompt": "different"})
    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["run_id"] == first.json()["run_id"]
    assert conflict.status_code == 409


def test_deferred_run_can_be_cancelled_and_cannot_execute_afterwards(client: TestClient) -> None:
    created = client.post(
        "/v1/runs",
        headers={**HEADERS, "Idempotency-Key": "cancel-me"},
        json={"prompt": "long task", "defer": True},
    ).json()
    cancelled = client.post(f"/v1/runs/{created['run_id']}/cancel", headers=HEADERS)
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(f"/v1/runs/{created['run_id']}/execute", headers=HEADERS).status_code == 409


def test_tenant_isolation_role_checks_and_prompt_budget(client: TestClient) -> None:
    created = client.post(
        "/v1/runs",
        headers={**HEADERS, "Idempotency-Key": "private"},
        json={"prompt": "tenant data", "defer": True},
    ).json()
    other = {**HEADERS, "X-Tenant-ID": "tenant-b"}
    assert client.get(f"/v1/runs/{created['run_id']}", headers=other).status_code == 404
    no_role = {**HEADERS, "X-Roles": "reader", "Idempotency-Key": "denied"}
    assert client.post("/v1/runs", headers=no_role, json={"prompt": "x"}).status_code == 403
    assert client.post("/v1/runs", headers=HEADERS, json={"prompt": "x"}).status_code == 400


def test_sse_cursor_replays_only_later_events(client: TestClient) -> None:
    run = client.post(
        "/v1/runs",
        headers={**HEADERS, "Idempotency-Key": "cursor"},
        json={"prompt": "replay events"},
    ).json()
    all_events = client.get(f"/v1/runs/{run['run_id']}/events", headers=HEADERS).text
    first_id = int(
        next(
            line.split(": ", 1)[1]
            for line in all_events.splitlines()
            if line.startswith("id: ")
        )
    )
    later = client.get(
        f"/v1/runs/{run['run_id']}/events?after={first_id}", headers=HEADERS
    ).text
    assert f"id: {first_id}\n" not in later
    assert "event: succeeded" in later


def test_prompt_budget_and_observability_role_are_enforced(client: TestClient) -> None:
    oversized = client.post(
        "/v1/runs",
        headers={**HEADERS, "Idempotency-Key": "oversized"},
        json={"prompt": "x" * 20_001},
    )
    assert oversized.status_code == 413
    run_only = {**HEADERS, "X-Roles": "project:run"}
    assert client.get("/metrics", headers=run_only).status_code == 403


@pytest.mark.parametrize("project_id", range(1, 11))
def test_run_survives_service_recreation(project_id: int, tmp_path: Path) -> None:
    database = tmp_path / f"restart-{project_id}.db"
    settings = ServiceSettings(database_path=database)
    first = TestClient(create_project_app(project_id, settings=settings))
    run = first.post(
        "/v1/runs",
        headers={**HEADERS, "Idempotency-Key": "restart"},
        json={"prompt": "persist me"},
    ).json()
    restarted = TestClient(create_project_app(project_id, settings=settings))
    restored = restarted.get(f"/v1/runs/{run['run_id']}", headers=HEADERS)
    assert restored.status_code == 200
    assert restored.json() == run


def test_failed_executor_is_redacted_and_persisted(tmp_path: Path) -> None:
    def fail(project_id: int, prompt: str):  # type: ignore[no-untyped-def]
        raise RuntimeError(f"secret must not leak: {project_id}:{prompt}")

    app = create_project_app(
        1,
        settings=ServiceSettings(database_path=tmp_path / "failed.db"),
        executor=fail,
    )
    response = TestClient(app).post(
        "/v1/runs",
        headers={**HEADERS, "Idempotency-Key": "failure"},
        json={"prompt": "sensitive input"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert response.json()["data"] == {"error_type": "RuntimeError"}
    assert "secret" not in response.text
