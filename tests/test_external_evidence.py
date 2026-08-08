from pathlib import Path
from typing import Any

import yaml

from scripts.validate_external_evidence import (
    REQUIRED_RIGHTS_CATEGORIES,
    load_evidence,
    validate_directory,
    validate_record,
)

COMMIT = "a" * 40
NO_FINDINGS = {"p0": 0, "p1": 0, "p2": 1, "p3": 0}
ROOT = Path(__file__).parents[1]


def _base(evidence_type: str, record_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "evidence_type": evidence_type,
        "record_id": record_id,
        "checked_at": "2026-08-08",
        "source_commit": COMMIT,
    }


def _write(directory: Path, name: str, document: dict[str, Any]) -> None:
    (directory / name).write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _valid_review(role: str) -> dict[str, Any]:
    document = _base("independent_review", f"review-{role.replace('_', '-')}")
    document.update(
        {
            "role": role,
            "reviewer_id": f"anonymous-{role}",
            "independent": True,
            "conflict_statement_recorded": True,
            "sampled_artifacts": [f"artifact-{index}" for index in range(6)],
            "decision": "pass",
            "open_findings": NO_FINDINGS,
            "private_source_reference": f"controlled-record-{role}",
        }
    )
    return document


def _write_valid_evidence_set(directory: Path) -> None:
    directory.mkdir()
    for role in ("agent_engineer", "python_engineer", "chinese_editor"):
        _write(directory, f"review-{role}.yml", _valid_review(role))

    learner = _base("learner_trial", "learner-trial-001")
    learner.update(
        {
            "participants": 3,
            "opened_html_within_15_min": 3,
            "project_2_without_operator": 2,
            "mean_core_exercise_score": 84,
            "open_findings": NO_FINDINGS,
        }
    )
    _write(directory, "learner.yml", learner)

    pilot = _base("enterprise_pilot", "enterprise-pilot-001")
    pilot.update(
        {
            "participants": 8,
            "duration_minutes": 270,
            "environment_success_rate": 0.95,
            "core_lab_completion_rate": 0.85,
            "average_gain_percentage_points": 24,
            "repository_only_delivery": True,
            "open_findings": NO_FINDINGS,
        }
    )
    _write(directory, "enterprise.yml", pilot)

    device = _base("device_print_qa", "device-print-qa-001")
    device.update(
        {
            "devices": [
                {
                    "category": category,
                    "os_and_reader": f"observed {category} reader",
                    "checks_passed": ["navigation", "diagram", "code", "table"],
                    "result": "pass",
                }
                for category in ("ios_phone", "ios_tablet", "android_phone")
            ],
            "print_proof": {
                "vendor_or_device": "controlled print vendor",
                "binding_and_paper": "A4 duplex 80gsm sample",
                "margins_passed": True,
                "grayscale_passed": True,
                "diagrams_passed": True,
                "code_passed": True,
                "result": "pass",
            },
            "open_findings": NO_FINDINGS,
        }
    )
    _write(directory, "device.yml", device)

    rights = _base("rights_review", "rights-review-001")
    rights.update(
        {
            "reviewer_id": "anonymous-rights-reviewer",
            "independent": True,
            "professional_capacity": True,
            "categories_reviewed": sorted(REQUIRED_RIGHTS_CATEGORIES),
            "decision": "approved",
            "open_findings": NO_FINDINGS,
            "private_opinion_reference": "controlled-opinion-record-001",
        }
    )
    _write(directory, "rights.yml", rights)


def test_complete_external_evidence_set_passes(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    _write_valid_evidence_set(evidence)

    result = validate_directory(evidence)

    assert result["valid"] is True
    assert result["records"] == 7
    assert result["issues"] == []


def test_threshold_failure_is_not_accepted(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    _write_valid_evidence_set(evidence)
    learner_path = evidence / "learner.yml"
    learner = yaml.safe_load(learner_path.read_text(encoding="utf-8"))
    learner["project_2_without_operator"] = 1
    _write(evidence, "learner.yml", learner)

    result = validate_directory(evidence)

    assert result["valid"] is False
    assert any("two thirds" in issue for issue in result["issues"])


def test_empty_repository_evidence_cannot_close_p9(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    result = validate_directory(evidence)

    assert result["valid"] is False
    assert result["records"] == 0
    assert len(result["issues"]) == 6


def test_distributed_templates_are_structurally_valid_but_fail_closed() -> None:
    templates = sorted((ROOT / "external-validation/templates").glob("*.yml"))

    assert len(templates) == 5
    for template in templates:
        record = load_evidence(template)
        assert validate_record(record), f"{template} must not be a pre-approved record"
