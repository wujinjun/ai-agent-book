from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_agent_book.apps.langgraph_research import (
    DurableResearchService,
    EvidenceItem,
    SourcePolicy,
    attach_durable_research_routes,
)
from ai_agent_book.project_service import ServiceSettings, create_project_app


def _evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            title="Checkpoint",
            url="https://docs.example.test/checkpoint",
            content="Checkpoint 保存工作流状态。",
        ),
        EvidenceItem(
            title="Approval",
            url="https://research.example.test/approval",
            content="Interrupt 等待人工审批。",
        ),
    ]


def _service(path: Path) -> DurableResearchService:
    return DurableResearchService(
        path,
        source_policy=SourcePolicy(
            allowed_domains=frozenset({"docs.example.test", "research.example.test"})
        ),
    )


def test_run_pauses_and_resumes_after_service_restart(tmp_path: Path) -> None:
    database = tmp_path / "research.db"
    service = _service(database)
    run = service.submit("如何恢复 Agent？", _evidence(), tenant_id="a")
    paused = service.process_next(tenant_id="a")
    assert paused is not None and paused.status == "awaiting_approval"
    restarted = _service(database)
    completed = restarted.approve("a", run.run_id, approved=True)
    assert completed.status == "completed"
    assert "Checkpoint" in completed.report


def test_denied_approval_terminates_without_report(tmp_path: Path) -> None:
    service = _service(tmp_path / "research.db")
    run = service.submit("topic", _evidence(), tenant_id="a")
    service.process_next(tenant_id="a")
    cancelled = service.approve("a", run.run_id, approved=False)
    assert cancelled.status == "cancelled"
    assert cancelled.report == ""


def test_source_policy_rejects_non_https_unknown_and_single_source(tmp_path: Path) -> None:
    service = _service(tmp_path / "research.db")
    with pytest.raises(ValueError):
        service.submit("topic", [_evidence()[0]], tenant_id="a")
    invalid = _evidence()
    invalid[1] = invalid[1].model_copy(update={"url": "http://evil.test/data"})
    with pytest.raises(ValueError):
        service.submit("topic", invalid, tenant_id="a")
    unknown = _evidence()
    unknown[1] = unknown[1].model_copy(update={"url": "https://evil.test/data"})
    with pytest.raises(PermissionError):
        service.submit("topic", unknown, tenant_id="a")


def test_evidence_tampering_fails_digest_check_without_leaking_content(tmp_path: Path) -> None:
    service = _service(tmp_path / "research.db")
    run = service.submit("topic", _evidence(), tenant_id="a")
    with service._connect() as db:
        db.execute(
            "UPDATE research_runs SET evidence_json='[]' WHERE run_id=?", (run.run_id,)
        )
    failed = service.process_next(tenant_id="a")
    assert failed is not None and failed.status == "failed"
    assert failed.error_type == "ValueError"


def test_running_lease_is_recovered_and_tenants_are_isolated(tmp_path: Path) -> None:
    service = _service(tmp_path / "research.db")
    run = service.submit("topic", _evidence(), tenant_id="a")
    with service._connect() as db:
        db.execute("UPDATE research_runs SET status='running' WHERE run_id=?", (run.run_id,))
    assert service.recover_incomplete() == 1
    assert service.process_next(tenant_id="b") is None
    assert service.process_next(tenant_id="a") is not None
    with pytest.raises(KeyError):
        service.get("b", run.run_id)


def test_durable_research_api_enforces_roles_and_completes(tmp_path: Path) -> None:
    service = _service(tmp_path / "research.db")
    app = create_project_app(
        8, settings=ServiceSettings(database_path=tmp_path / "runs.db")
    )
    attach_durable_research_routes(app, service)
    client = TestClient(app)
    headers = {
        "X-Tenant-ID": "a",
        "X-User-ID": "admin",
        "X-Roles": "project:run,project:admin,project:approve",
    }
    created = client.post(
        "/v1/research/runs",
        headers=headers,
        json={"topic": "Agent 恢复", "evidence": [item.model_dump() for item in _evidence()]},
    )
    run_id = created.json()["run_id"]
    assert client.post("/v1/research/worker/process-one", headers=headers).json()[
        "status"
    ] == "awaiting_approval"
    completed = client.post(
        f"/v1/research/runs/{run_id}/approval",
        headers=headers,
        json={"approved": True},
    )
    assert completed.json()["status"] == "completed"
    denied = {**headers, "X-Roles": "project:run"}
    assert client.post("/v1/research/worker/process-one", headers=denied).status_code == 403
