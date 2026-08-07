"""Execute candidate drivers in isolated Python environments and collect evidence."""

import json
import os
import subprocess
import sys
from pathlib import Path

from framework_comparison.domain import CandidateEvidence


def _run_candidate(python: Path, module: str, *, runs: int) -> CandidateEvidence:
    package_src = Path(__file__).parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_src)
    env["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    completed = subprocess.run(
        [str(python), "-m", module, "--runs", str(runs)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    return CandidateEvidence.model_validate(json.loads(completed.stdout))


def collect(
    *, openai_python: Path, pydanticai_python: Path, runs: int = 20
) -> list[CandidateEvidence]:
    candidates = [
        (Path(sys.executable), "framework_comparison.candidates.native_runtime"),
        (openai_python, "framework_comparison.candidates.openai_agents_sdk"),
        (pydanticai_python, "framework_comparison.candidates.pydanticai"),
    ]
    evidence: list[CandidateEvidence] = []
    for python, module in candidates:
        if not python.is_file():
            raise FileNotFoundError(f"candidate Python not found: {python}")
        evidence.append(_run_candidate(python, module, runs=runs))
    return evidence
