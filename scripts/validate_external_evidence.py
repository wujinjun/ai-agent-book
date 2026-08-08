#!/usr/bin/env python3
"""Validate anonymized P9 external evidence against the published acceptance rules."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, TypedDict

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_DIR = ROOT / "external-validation/evidence"
REQUIRED_REVIEW_ROLES = {"agent_engineer", "python_engineer", "chinese_editor"}
REQUIRED_DEVICE_CATEGORIES = {"ios_phone", "ios_tablet", "android_phone"}
REQUIRED_DEVICE_CHECKS = {"navigation", "diagram", "code", "table"}
REQUIRED_RIGHTS_CATEGORIES = {
    "content_license",
    "code_license",
    "dependencies",
    "contributions",
    "fonts",
    "images_and_diagrams",
    "trademarks",
    "distribution_terms",
}


class EvidenceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    record_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")]
    checked_at: date
    source_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]


class FindingCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p0: Annotated[int, Field(ge=0)] = 0
    p1: Annotated[int, Field(ge=0)] = 0
    p2: Annotated[int, Field(ge=0)] = 0
    p3: Annotated[int, Field(ge=0)] = 0


class IndependentReview(EvidenceBase):
    evidence_type: Literal["independent_review"]
    role: Literal["agent_engineer", "python_engineer", "chinese_editor"]
    reviewer_id: Annotated[str, Field(min_length=3, max_length=64)]
    independent: bool
    conflict_statement_recorded: bool
    sampled_artifacts: Annotated[list[str], Field(min_length=6)]
    decision: Literal["pass", "conditional", "fail"]
    open_findings: FindingCounts
    private_source_reference: Annotated[str, Field(min_length=8, max_length=256)]


class LearnerTrial(EvidenceBase):
    evidence_type: Literal["learner_trial"]
    participants: Annotated[int, Field(ge=3)]
    opened_html_within_15_min: Annotated[int, Field(ge=0)]
    project_2_without_operator: Annotated[int, Field(ge=0)]
    mean_core_exercise_score: Annotated[float, Field(ge=0, le=100)]
    open_findings: FindingCounts


class EnterprisePilot(EvidenceBase):
    evidence_type: Literal["enterprise_pilot"]
    participants: Annotated[int, Field(ge=6, le=12)]
    duration_minutes: Annotated[int, Field(ge=240)]
    environment_success_rate: Annotated[float, Field(ge=0, le=1)]
    core_lab_completion_rate: Annotated[float, Field(ge=0, le=1)]
    average_gain_percentage_points: Annotated[float, Field(ge=-100, le=100)]
    repository_only_delivery: bool
    open_findings: FindingCounts


class DeviceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["ios_phone", "ios_tablet", "android_phone", "android_tablet"]
    os_and_reader: Annotated[str, Field(min_length=3, max_length=128)]
    checks_passed: set[Literal["navigation", "diagram", "code", "table", "search", "links"]]
    result: Literal["pass", "fail"]


class PrintProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_or_device: Annotated[str, Field(min_length=3, max_length=128)]
    binding_and_paper: Annotated[str, Field(min_length=3, max_length=128)]
    margins_passed: bool
    grayscale_passed: bool
    diagrams_passed: bool
    code_passed: bool
    result: Literal["pass", "fail"]


class DevicePrintQA(EvidenceBase):
    evidence_type: Literal["device_print_qa"]
    devices: Annotated[list[DeviceResult], Field(min_length=3)]
    print_proof: PrintProof
    open_findings: FindingCounts


class RightsReview(EvidenceBase):
    evidence_type: Literal["rights_review"]
    reviewer_id: Annotated[str, Field(min_length=3, max_length=64)]
    independent: bool
    professional_capacity: bool
    categories_reviewed: set[str]
    decision: Literal["approved", "approved_with_conditions", "not_approved"]
    open_findings: FindingCounts
    private_opinion_reference: Annotated[str, Field(min_length=8, max_length=256)]


type Evidence = (
    IndependentReview | LearnerTrial | EnterprisePilot | DevicePrintQA | RightsReview
)
EVIDENCE_MODELS: dict[str, type[EvidenceBase]] = {
    "independent_review": IndependentReview,
    "learner_trial": LearnerTrial,
    "enterprise_pilot": EnterprisePilot,
    "device_print_qa": DevicePrintQA,
    "rights_review": RightsReview,
}


class ValidationSummary(TypedDict):
    valid: bool
    records: int
    counts: dict[str, int]
    review_roles: list[str]
    source_commits: list[str]
    issues: list[str]


def load_evidence(path: Path) -> Evidence:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("document must be a mapping")
    evidence_type = raw.get("evidence_type")
    model = EVIDENCE_MODELS.get(str(evidence_type))
    if model is None:
        raise ValueError(f"unsupported evidence_type: {evidence_type!r}")
    return model.model_validate(raw)  # type: ignore[return-value]


def _no_open_high_findings(record: Evidence) -> bool:
    return record.open_findings.p0 == 0 and record.open_findings.p1 == 0


def validate_record(record: Evidence) -> list[str]:
    issues: list[str] = []
    if set(record.source_commit) == {"0"}:
        issues.append("source_commit placeholder must be replaced")
    if record.checked_at > date.today():
        issues.append("checked_at cannot be in the future")
    if not _no_open_high_findings(record):
        issues.append("open P0/P1 findings must be zero")

    if isinstance(record, IndependentReview):
        if not record.independent:
            issues.append("reviewer must be independent from the maintainer role review")
        if not record.conflict_statement_recorded:
            issues.append("reviewer conflict statement must be recorded")
        if record.decision != "pass":
            issues.append("independent review decision must be pass")
    elif isinstance(record, LearnerTrial):
        if record.opened_html_within_15_min != record.participants:
            issues.append("every learner must open HTML within 15 minutes")
        if record.project_2_without_operator / record.participants < 2 / 3:
            issues.append("at least two thirds must complete project 2 without operator action")
        if record.mean_core_exercise_score < 80:
            issues.append("mean core exercise score must be at least 80")
    elif isinstance(record, EnterprisePilot):
        if record.environment_success_rate < 0.90:
            issues.append("environment success rate must be at least 0.90")
        if record.core_lab_completion_rate < 0.80:
            issues.append("core lab completion rate must be at least 0.80")
        if record.average_gain_percentage_points < 20:
            issues.append("average pre/post gain must be at least 20 percentage points")
        if not record.repository_only_delivery:
            issues.append("trainer must deliver using repository materials only")
    elif isinstance(record, DevicePrintQA):
        categories = {item.category for item in record.devices if item.result == "pass"}
        missing_devices = REQUIRED_DEVICE_CATEGORIES - categories
        if missing_devices:
            issues.append(f"missing passing physical device categories: {sorted(missing_devices)}")
        for item in record.devices:
            missing_checks = REQUIRED_DEVICE_CHECKS - item.checks_passed
            if item.result != "pass" or missing_checks:
                issues.append(
                    f"device {item.category} failed or missed checks: {sorted(missing_checks)}"
                )
        proof = record.print_proof
        if proof.result != "pass" or not all(
            (proof.margins_passed, proof.grayscale_passed, proof.diagrams_passed, proof.code_passed)
        ):
            issues.append("physical print proof must pass margins, grayscale, diagrams and code")
    elif isinstance(record, RightsReview):
        if not record.independent or not record.professional_capacity:
            issues.append("rights review must be independent and performed professionally")
        missing_categories = REQUIRED_RIGHTS_CATEGORIES - record.categories_reviewed
        if missing_categories:
            issues.append(f"rights review missing categories: {sorted(missing_categories)}")
        if record.decision != "approved":
            issues.append(
                "commercial distribution decision must be approved without open conditions"
            )
    return issues


def validate_directory(
    directory: Path,
    *,
    require_all: bool = True,
    expected_source_commit: str | None = None,
) -> ValidationSummary:
    records: list[Evidence] = []
    issues: list[str] = []
    for path in sorted(directory.glob("*.yml")):
        try:
            record = load_evidence(path)
        except (OSError, ValueError, ValidationError) as exc:
            issues.append(f"{path.name}: {exc}")
            continue
        records.append(record)
        issues.extend(f"{path.name}: {issue}" for issue in validate_record(record))

    counts: dict[str, int] = {}
    for record in records:
        counts[record.evidence_type] = counts.get(record.evidence_type, 0) + 1
    review_roles = {
        record.role for record in records if isinstance(record, IndependentReview)
    }
    reviewer_ids = [
        record.reviewer_id for record in records if isinstance(record, IndependentReview)
    ]
    record_ids = [record.record_id for record in records]
    source_commits = {record.source_commit for record in records}
    if expected_source_commit is not None:
        if re.fullmatch(r"[0-9a-f]{40}", expected_source_commit) is None:
            issues.append("expected source commit must be a 40-character lowercase Git SHA")
        unexpected_commits = source_commits - {expected_source_commit}
        if unexpected_commits:
            issues.append(
                "external evidence targets a different commit: "
                f"expected {expected_source_commit}, found {sorted(unexpected_commits)}"
            )
    if len(record_ids) != len(set(record_ids)):
        issues.append("record_id values must be unique")
    if require_all:
        missing_roles = REQUIRED_REVIEW_ROLES - review_roles
        if missing_roles:
            issues.append(f"missing independent review roles: {sorted(missing_roles)}")
        if len(reviewer_ids) != len(set(reviewer_ids)):
            issues.append("the three independent reviews require distinct reviewer IDs")
        if counts.get("independent_review", 0) != 3:
            issues.append("exactly three independent_review records are required")
        if records and len(source_commits) != 1:
            issues.append("all external evidence must target the same source commit")
        for required in ("learner_trial", "enterprise_pilot", "device_print_qa", "rights_review"):
            if counts.get(required, 0) != 1:
                issues.append(f"exactly one {required} record is required")

    return {
        "valid": not issues,
        "records": len(records),
        "counts": counts,
        "review_roles": sorted(review_roles),
        "source_commits": sorted(source_commits),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_dir", nargs="?", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--expected-source-commit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate_directory(
        args.evidence_dir,
        require_all=not args.allow_partial,
        expected_source_commit=args.expected_source_commit,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"External evidence valid={result['valid']}, records={result['records']}, "
            f"issues={len(result['issues'])}"
        )
        for issue in result["issues"]:
            print(f"- {issue}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
