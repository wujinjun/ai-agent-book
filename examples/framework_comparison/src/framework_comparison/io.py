"""Load and validate benchmark fixtures and evidence."""

import hashlib
import json
from pathlib import Path

from framework_comparison.domain import BenchmarkSpec, CandidateEvidence

EXAMPLE_ROOT = Path(__file__).parents[2]


def load_spec(path: Path | None = None) -> BenchmarkSpec:
    source = path or EXAMPLE_ROOT / "fixtures" / "research-spec.json"
    return BenchmarkSpec.model_validate_json(source.read_text(encoding="utf-8"))


def load_evidence(path: Path | None = None) -> list[CandidateEvidence]:
    source = path or EXAMPLE_ROOT / "fixtures" / "verified-evidence.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    return [CandidateEvidence.model_validate(item) for item in payload["candidates"]]


def dump_evidence(path: Path, evidence: list[CandidateEvidence]) -> None:
    payload = {
        "schema_version": 1,
        "generated_at": "2026-08-07",
        "candidates": [item.model_dump(mode="json") for item in evidence],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_evidence_sources(evidence: list[CandidateEvidence]) -> None:
    candidate_root = EXAMPLE_ROOT / "src" / "framework_comparison" / "candidates"
    for item in evidence:
        source = candidate_root / item.implementation_path
        if not source.is_file():
            raise ValueError(f"implementation evidence is missing: {source}")
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != item.implementation_sha256:
            raise ValueError(f"implementation evidence is stale: {item.candidate}")
