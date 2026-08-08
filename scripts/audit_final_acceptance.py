#!/usr/bin/env python3
"""Validate full or explicitly repository-scoped P9 completion claims."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_external_evidence import (  # noqa: E402
    DEFAULT_EVIDENCE_DIR,
    validate_directory,
)

MATRIX = ROOT / "notes/p9-acceptance.yml"
REQUIRED_GAP_FIELDS = {"id", "owner", "reason", "next_review"}
REQUIRED_EXCLUSION_FIELDS = {"id", "reason", "status"}
REQUIRED_EXTERNAL_EXCLUSIONS = {
    "independent-agent-review",
    "independent-python-review",
    "independent-chinese-edit",
    "learner-trial",
    "enterprise-pilot",
    "physical-device-and-print",
    "legal-and-rights-opinion",
}
REQUIRED_EVIDENCE = {
    "chapters_reviewed",
    "project_clis_run",
    "project_service_images_built",
    "project_service_healthchecks_passed",
    "isolated_examples_verified",
    "python",
    "tests",
    "diagrams",
    "html",
    "pdf",
    "epub",
    "training_pptx",
    "secret_scan",
    "privacy_scan",
    "distribution_preflight",
    "external_evidence_intake",
    "final_release_gate",
}


def load_matrix(path: Path = MATRIX) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("P9 matrix must be a mapping")
    return document


def validate_matrix(document: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    scope = document.get("repository_scope", {})
    missing_evidence = REQUIRED_EVIDENCE - set(scope)
    if missing_evidence:
        issues.append(f"missing repository evidence: {sorted(missing_evidence)}")

    scores = document.get("scores", {})
    score_items = {key: value for key, value in scores.items() if key != "kind"}
    if len(score_items) != 5:
        issues.append("exactly five target scores are required")
    for name, score in score_items.items():
        if not isinstance(score, dict) or not {
            "current",
            "repository_target",
            "full_target",
        } <= set(score):
            issues.append(
                f"score {name} must contain current, repository_target and full_target"
            )

    gaps = document.get("open_gaps", [])
    for index, gap in enumerate(gaps):
        missing = REQUIRED_GAP_FIELDS - set(gap)
        if missing:
            issues.append(f"gap {index} missing fields: {sorted(missing)}")
            continue
        try:
            date.fromisoformat(str(gap["next_review"]))
        except ValueError:
            issues.append(f"gap {gap['id']} has invalid next_review")
        for field in ("owner", "reason"):
            if not str(gap[field]).strip():
                issues.append(f"gap {gap['id']} has empty {field}")

    status = document.get("status")
    if status == "complete_repository_scope":
        if gaps:
            issues.append("repository-scope completion cannot contain open gaps")
        decision = document.get("scope_decision")
        if not isinstance(decision, dict) or decision.get("external_validation") != "excluded":
            issues.append("repository-scope completion requires an explicit exclusion decision")
        exclusions = document.get("excluded_external_gates", [])
        exclusion_ids: set[str] = set()
        for index, exclusion in enumerate(exclusions):
            if not isinstance(exclusion, dict):
                issues.append(f"external exclusion {index} must be a mapping")
                continue
            missing = REQUIRED_EXCLUSION_FIELDS - set(exclusion)
            if missing:
                issues.append(f"external exclusion {index} missing fields: {sorted(missing)}")
                continue
            exclusion_ids.add(str(exclusion["id"]))
            if exclusion["status"] != "excluded_not_passed":
                issues.append(
                    f"external exclusion {exclusion['id']} must be excluded_not_passed"
                )
            if not str(exclusion["reason"]).strip():
                issues.append(f"external exclusion {exclusion['id']} has empty reason")
        if exclusion_ids != REQUIRED_EXTERNAL_EXCLUSIONS:
            issues.append(
                "repository-scope completion must list exactly the seven external exclusions"
            )
        for name, score in score_items.items():
            if score["current"] < score["repository_target"]:
                issues.append(f"repository-scope score below target: {name}")

    if status == "complete":
        if gaps:
            issues.append("complete status cannot contain open gaps")
        for name, score in score_items.items():
            if score["current"] < score["full_target"]:
                issues.append(f"complete status has score below target: {name}")
        external = validate_directory(DEFAULT_EVIDENCE_DIR)
        issues.extend(f"external evidence: {issue}" for issue in external["issues"])
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--require-repository-complete", action="store_true")
    args = parser.parse_args()
    document = load_matrix()
    issues = validate_matrix(document)
    if args.require_complete and document.get("status") != "complete":
        issues.append(f"P9 status is {document.get('status')}, not complete")
    if (
        args.require_repository_complete
        and document.get("status") != "complete_repository_scope"
    ):
        issues.append(
            f"P9 status is {document.get('status')}, not complete_repository_scope"
        )
    for issue in issues:
        print(issue)
    if issues:
        return 1
    print(
        f"P9 acceptance matrix valid: status={document['status']}, "
        f"open_gaps={len(document['open_gaps'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
