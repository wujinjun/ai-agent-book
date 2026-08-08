from pathlib import Path

import yaml

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


def test_docker_builds_include_declared_license_file() -> None:
    dockerfiles = [ROOT / "projects/service.Dockerfile"]
    dockerfiles.extend(sorted((ROOT / "projects").glob("[0-9][0-9]-*/Dockerfile")))

    for dockerfile in dockerfiles:
        content = dockerfile.read_text(encoding="utf-8")
        assert "COPY pyproject.toml README.md LICENSE-CODE ./" in content, (
            f"{dockerfile} must copy the license declared by pyproject.toml"
        )


def test_durable_project_services_store_all_state_in_writable_volumes() -> None:
    compose = yaml.safe_load((ROOT / "projects/docker-compose.yml").read_text(encoding="utf-8"))
    project_4 = compose["services"]["project-4"]["environment"]
    project_8 = compose["services"]["project-8"]["environment"]

    assert set(project_4.values()) == {
        "/app/data/project-4.db",
        "/app/data/project-4-pipeline.db",
        "/app/data/imports",
    }
    assert set(project_8.values()) == {
        "/app/data/project-8.db",
        "/app/data/project-8-research.db",
    }


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
