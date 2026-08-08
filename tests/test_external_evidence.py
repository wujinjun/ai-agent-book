import hashlib
import json
import subprocess
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


def _base(
    evidence_type: str,
    record_id: str,
    *,
    source_commit: str,
    manifest_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "evidence_type": evidence_type,
        "record_id": record_id,
        "checked_at": "2026-08-08",
        "source_commit": source_commit,
        "candidate_manifest_sha256": manifest_hash,
    }


def _write(directory: Path, name: str, document: dict[str, Any]) -> None:
    (directory / name).write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _valid_review(role: str, *, source_commit: str, manifest_hash: str) -> dict[str, Any]:
    document = _base(
        "independent_review",
        f"review-{role.replace('_', '-')}",
        source_commit=source_commit,
        manifest_hash=manifest_hash,
    )
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


def _write_candidate_manifest(directory: Path, source_commit: str) -> str:
    manifest = {
        "schema_version": 1,
        "version": "candidate",
        "source_commit": source_commit,
        "artifacts": [
            {"role": role, "file": f"{role}.bin", "bytes": 1, "sha256": "c" * 64}
            for role in ("book_pdf", "book_epub", "training_pptx", "release_notes")
        ],
    }
    payload = json.dumps(manifest, ensure_ascii=False, indent=2).encode() + b"\n"
    candidate = directory.parent / "candidate"
    candidate.mkdir()
    (candidate / "release-manifest.json").write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _write_valid_evidence_set(directory: Path, *, source_commit: str = COMMIT) -> None:
    directory.mkdir(parents=True)
    manifest_hash = _write_candidate_manifest(directory, source_commit)
    for role in ("agent_engineer", "python_engineer", "chinese_editor"):
        _write(
            directory,
            f"review-{role}.yml",
            _valid_review(
                role,
                source_commit=source_commit,
                manifest_hash=manifest_hash,
            ),
        )

    learner = _base(
        "learner_trial",
        "learner-trial-001",
        source_commit=source_commit,
        manifest_hash=manifest_hash,
    )
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

    pilot = _base(
        "enterprise_pilot",
        "enterprise-pilot-001",
        source_commit=source_commit,
        manifest_hash=manifest_hash,
    )
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

    device = _base(
        "device_print_qa",
        "device-print-qa-001",
        source_commit=source_commit,
        manifest_hash=manifest_hash,
    )
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

    rights = _base(
        "rights_review",
        "rights-review-001",
        source_commit=source_commit,
        manifest_hash=manifest_hash,
    )
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


def test_external_evidence_must_target_the_release_commit(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    _write_valid_evidence_set(evidence)

    result = validate_directory(evidence, expected_source_commit="b" * 40)

    assert result["valid"] is False
    assert any("different commit" in issue for issue in result["issues"])

    manifest = evidence.parent / "candidate/release-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    tampered = validate_directory(evidence)
    assert tampered["valid"] is False
    assert any("manifest hash mismatch" in issue for issue in tampered["issues"])
    assert any("schema_version" in issue for issue in tampered["issues"])
    assert any("artifacts must be a list" in issue for issue in tampered["issues"])


def test_release_lineage_allows_evidence_only_and_rejects_reviewed_content_changes(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repository,
        check=True,
    )
    (repository / "README.md").write_text("candidate\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate"], cwd=repository, check=True)
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()

    evidence = repository / "external-validation/evidence"
    _write_valid_evidence_set(evidence, source_commit=source_commit)
    subprocess.run(["git", "add", "external-validation"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "evidence"], cwd=repository, check=True)
    evidence_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()

    accepted = validate_directory(
        evidence,
        release_commit=evidence_commit,
        repository=repository,
    )
    assert accepted["valid"] is True

    (repository / "reviewed-content.md").write_text("changed after review\n", encoding="utf-8")
    subprocess.run(["git", "add", "reviewed-content.md"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "forbidden"], cwd=repository, check=True)
    forbidden_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()

    rejected = validate_directory(
        evidence,
        release_commit=forbidden_commit,
        repository=repository,
    )
    assert rejected["valid"] is False
    assert any("reviewed content" in issue for issue in rejected["issues"])


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
