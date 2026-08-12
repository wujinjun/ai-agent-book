from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_agent_book.apps.knowledge_agent import (
    GoldenCase,
    VersionedKnowledgePipeline,
    attach_knowledge_routes,
)
from ai_agent_book.project_service import ServiceSettings, create_project_app


def _source(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _golden() -> list[GoldenCase]:
    return [GoldenCase(query="谁保存工作流状态？", expected_text="Checkpoint")]


def test_submission_is_idempotent_and_worker_activates_passing_index(tmp_path: Path) -> None:
    source = _source(tmp_path / "guide.md", "Checkpoint 保存工作流状态并支持恢复。")
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    first, created = pipeline.submit(source, tenant_id="a", golden_cases=_golden())
    replay, replay_created = pipeline.submit(source, tenant_id="a", golden_cases=_golden())
    completed = pipeline.process_next()
    assert created is True and replay_created is False
    assert replay.job_id == first.job_id
    assert completed is not None and completed.status == "succeeded"
    assert pipeline.active_version("a") is not None
    assert pipeline.answer("如何保存状态？", tenant_id="a").citations


def test_rejected_candidate_does_not_replace_active_version(tmp_path: Path) -> None:
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    good = _source(tmp_path / "good.md", "Checkpoint 保存工作流状态并支持恢复。")
    pipeline.submit(good, tenant_id="a", golden_cases=_golden())
    pipeline.process_next()
    active = pipeline.active_version("a")
    bad = _source(tmp_path / "bad.md", "这是一份无关材料。")
    pipeline.submit(bad, tenant_id="a", golden_cases=_golden())
    pipeline.process_next()
    assert active is not None
    assert pipeline.active_version("a") == active


def test_active_index_is_tenant_isolated_and_survives_restart(tmp_path: Path) -> None:
    database = tmp_path / "pipeline.db"
    source = _source(tmp_path / "guide.md", "Checkpoint 保存工作流状态并支持恢复。")
    pipeline = VersionedKnowledgePipeline(database)
    pipeline.submit(source, tenant_id="a", golden_cases=_golden())
    pipeline.process_next()
    restarted = VersionedKnowledgePipeline(database)
    assert restarted.answer("如何保存状态？", tenant_id="a").citations
    assert restarted.answer("如何保存状态？", tenant_id="b").citations == []


def test_interrupted_job_returns_to_queue(tmp_path: Path) -> None:
    source = _source(tmp_path / "guide.md", "Checkpoint 保存工作流状态并支持恢复。")
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    job, _ = pipeline.submit(source, tenant_id="a", golden_cases=_golden())
    with pipeline._connect() as db:
        db.execute("UPDATE ingestion_jobs SET status='running' WHERE job_id=?", (job.job_id,))
    assert pipeline.recover_incomplete() == 1
    assert pipeline.process_next() is not None


def test_parser_failure_is_redacted_to_error_type(tmp_path: Path) -> None:
    unsupported = _source(tmp_path / "input.exe", "not a document")
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    pipeline.submit(unsupported, tenant_id="a", golden_cases=[])
    failed = pipeline.process_next()
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error_type == "ValueError"


def test_source_mutation_after_queue_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path / "guide.md", "Checkpoint 保存工作流状态并支持恢复。")
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    pipeline.submit(source, tenant_id="a", golden_cases=_golden())
    source.write_text("队列提交后被替换。", encoding="utf-8")
    failed = pipeline.process_next()
    assert failed is not None and failed.status == "failed"
    assert pipeline.active_version("a") is None


def test_knowledge_api_runs_tenant_scoped_ingestion_and_query(tmp_path: Path) -> None:
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    app = create_project_app(
        4, settings=ServiceSettings(database_path=tmp_path / "runs.db")
    )
    attach_knowledge_routes(app, pipeline, import_root=tmp_path / "imports")
    client = TestClient(app)
    headers = {
        "X-Tenant-ID": "tenant-a",
        "X-User-ID": "admin",
        "X-Roles": "project:run,project:admin",
    }
    created = client.post(
        "/v1/knowledge/ingestions",
        headers=headers,
        json={
            "content": "Checkpoint 保存工作流状态并支持恢复。",
            "golden_cases": [
                {"query": "谁保存工作流状态？", "expected_text": "Checkpoint"}
            ],
        },
    )
    assert created.status_code == 200
    processed = client.post("/v1/knowledge/worker/process-one", headers=headers)
    assert processed.json()["status"] == "succeeded"
    answer = client.post(
        "/v1/knowledge/query", headers=headers, json={"query": "如何保存状态？"}
    )
    assert answer.json()["citations"]
    other = {**headers, "X-Tenant-ID": "tenant-b"}
    assert client.post(
        "/v1/knowledge/query", headers=other, json={"query": "如何保存状态？"}
    ).json()["citations"] == []


def test_active_index_chunk_tampering_is_detected(tmp_path: Path) -> None:
    source = _source(tmp_path / "guide.md", "Checkpoint 保存工作流状态并支持恢复。")
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    pipeline.submit(source, tenant_id="a", golden_cases=_golden())
    pipeline.process_next()
    with pipeline._connect() as db:
        db.execute(
            "UPDATE index_versions SET chunks_json='[]' WHERE tenant_id='a' AND status='active'"
        )

    with pytest.raises(ValueError, match="digest mismatch"):
        pipeline.answer("如何保存状态？", tenant_id="a")


def test_archived_version_can_be_atomically_rolled_back_within_tenant(tmp_path: Path) -> None:
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    first_source = _source(
        tmp_path / "first.md", "Checkpoint 保存工作流状态并支持恢复。第一版。"
    )
    first_job, _ = pipeline.submit(first_source, tenant_id="a", golden_cases=_golden())
    first_completed = pipeline.process_next()
    assert first_completed is not None and first_completed.version_id

    second_source = _source(
        tmp_path / "second.md", "Checkpoint 保存工作流状态并支持恢复。第二版。"
    )
    pipeline.submit(second_source, tenant_id="a", golden_cases=_golden())
    pipeline.process_next()
    assert pipeline.active_version("a") != pipeline.active_version("b")

    rolled_back = pipeline.rollback("a", first_completed.version_id)

    assert rolled_back.version_id == first_completed.version_id
    assert "第一版" in pipeline.answer("第一版", tenant_id="a").text
    with pytest.raises(KeyError):
        pipeline.rollback("b", first_completed.version_id)


def test_rejected_version_cannot_be_activated_by_rollback(tmp_path: Path) -> None:
    pipeline = VersionedKnowledgePipeline(tmp_path / "pipeline.db")
    source = _source(tmp_path / "bad.md", "无关材料。")
    pipeline.submit(source, tenant_id="a", golden_cases=_golden())
    rejected = pipeline.process_next()
    assert rejected is not None and rejected.version_id

    with pytest.raises(KeyError):
        pipeline.rollback("a", rejected.version_id)
