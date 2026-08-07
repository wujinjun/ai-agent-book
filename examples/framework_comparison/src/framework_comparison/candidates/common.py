"""Candidate evidence helpers."""

import hashlib
import platform
from pathlib import Path
from statistics import quantiles
from typing import Literal

from framework_comparison.domain import CandidateEvidence, ResearchReport, ToolEvent
from framework_comparison.fixture import evaluate


def percentile_95(samples: list[float]) -> float:
    if len(samples) < 2:
        return samples[0]
    return quantiles(samples, n=100, method="inclusive")[94]


def build_evidence(
    *,
    candidate: Literal["native_runtime", "openai_agents_sdk", "pydanticai"],
    framework_version: str,
    report: ResearchReport,
    events: list[ToolEvent],
    latencies_ms: list[float],
    model_requests: int,
    state_export: dict[str, object],
    implementation_file: str,
) -> CandidateEvidence:
    path = Path(implementation_file)
    success, accuracy, recovered = evaluate(events, report)
    return CandidateEvidence(
        candidate=candidate,
        framework_version=framework_version,
        python_version=platform.python_version(),
        task_success=success,
        tool_accuracy=accuracy,
        recovered_from_transient=recovered,
        p95_latency_ms=max(percentile_95(latencies_ms), 0.001),
        cost_proxy_model_requests=model_requests,
        state_exported=bool(state_export),
        state_export=state_export,
        tool_events=events,
        report=report,
        implementation_path=path.name,
        implementation_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        runs=len(latencies_ms),
    )
