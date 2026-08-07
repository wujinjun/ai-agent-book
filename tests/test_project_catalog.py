from pathlib import Path

from ai_agent_book.project_catalog import PROJECTS, run_project

ROOT = Path(__file__).parents[1]


def test_all_ten_projects_are_registered() -> None:
    assert sorted(PROJECTS) == list(range(1, 11))
    assert all(project.features for project in PROJECTS.values())


def test_each_project_has_runnable_and_deployable_files() -> None:
    for project in PROJECTS.values():
        directory = ROOT / "projects" / f"{project.project_id:02d}-{project.slug}"
        required = ["README.md", "main.py", ".env.example", "Dockerfile"]
        if project.project_id < 10:
            required.append("api.py")
        for name in required:
            assert (directory / name).is_file(), f"missing {directory / name}"
        assert list((directory / "tests").glob("test_*.py")), f"missing project test: {directory}"
        dockerfile = (directory / "Dockerfile").read_text(encoding="utf-8")
        if project.project_id < 10:
            assert 'CMD ["python", "main.py"]' in dockerfile
            assert "ai_agent_book.project_api:app" not in dockerfile


def test_projects_run_offline_with_structured_results() -> None:
    for project_id in PROJECTS:
        result = run_project(project_id, "请执行离线演示")
        assert result.project_id == project_id
        assert result.status in {"completed", "approval_required"}
        assert result.output
        assert result.trace


def test_stock_project_separates_facts_from_inference_and_warns_user() -> None:
    result = run_project(7, "研究 DEMO 股票")

    assert "不构成投资建议" in result.output
    assert result.data["facts"]
    assert result.data["inferences"]
    assert result.data["as_of"]


def test_office_project_requires_approval_before_external_action() -> None:
    result = run_project(6, "总结邮件并生成日报")
    assert result.status == "approval_required"
    assert result.data["pending_actions"]


def test_enterprise_platform_is_tenant_scoped() -> None:
    result = run_project(10, "tenant-a: 创建一次 Agent 任务")
    assert result.data["tenant_id"] == "tenant-a"
    assert result.data["trace_id"]
