from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
MATRIX = ROOT / "notes/project-capability-matrix.yml"
MATURITY = {
    "concept",
    "vertical_slice",
    "service_template",
    "production_reference",
    "externally_validated",
}


def test_project_capability_matrix_has_ten_evidence_backed_projects() -> None:
    document = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
    projects = document["projects"]
    assert [project["id"] for project in projects] == list(range(1, 11))
    for project in projects:
        assert project["maturity"] in MATURITY
        for key in ("demo_entry", "api_entry", "domain_implementation", "dockerfile"):
            assert (ROOT / project[key]).is_file(), (project["id"], key)
        assert project["direct_tests"]
        assert all((ROOT / path).is_file() for path in project["direct_tests"])
        assert project["persistence_recovery"]
        assert project["side_effect_safety"]
        assert project["gaps"] or project["maturity"] == "externally_validated"


def test_production_references_expose_recovery_and_multiple_direct_tests() -> None:
    projects = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))["projects"]
    references = [p for p in projects if p["maturity"] == "production_reference"]
    assert {project["id"] for project in references} == {4, 8, 10}
    for project in references:
        assert len(project["direct_tests"]) >= 2
        assert any(
            term in project["persistence_recovery"]
            for term in ("恢复", "重放", "备份", "回滚")
        )
        assert project["external_adapter"] != "mock_only"
