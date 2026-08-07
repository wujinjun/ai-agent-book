"""Weighted scoring, sensitivity analysis and reversible ADR generation."""

from collections.abc import Iterable

from framework_comparison.domain import (
    BenchmarkSpec,
    CandidateEvidence,
    CandidateScore,
    ComparisonResult,
)


def _component_values(evidence: CandidateEvidence, *, cheapest: int) -> dict[str, float]:
    latency_budget_ms = 50.0
    return {
        "task_success": 5.0 if evidence.task_success else 0.0,
        "tool_accuracy": evidence.tool_accuracy * 5,
        "recovery": 5.0 if evidence.recovered_from_transient else 0.0,
        "state_export": 5.0 if evidence.state_exported else 0.0,
        "latency": min(5.0, 5.0 * latency_budget_ms / evidence.p95_latency_ms),
        "cost_proxy": min(5.0, 5.0 * cheapest / evidence.cost_proxy_model_requests),
        "implementation_evidence": 5.0 if evidence.implementation_sha256 else 0.0,
    }


def _score_with_weights(
    evidence: list[CandidateEvidence], weights: dict[str, float]
) -> list[CandidateScore]:
    cheapest = min(item.cost_proxy_model_requests for item in evidence)
    scored: list[CandidateScore] = []
    for item in evidence:
        components = _component_values(item, cheapest=cheapest)
        total = sum(weights[name] * components[name] for name in weights)
        scored.append(
            CandidateScore(
                candidate=item.candidate,
                total=round(total, 4),
                components={name: round(value, 4) for name, value in components.items()},
                confidence=0.95,
            )
        )
    return sorted(scored, key=lambda item: (-item.total, item.candidate))


def _sensitivity_weights(weights: dict[str, float]) -> Iterable[dict[str, float]]:
    yield weights
    for target in weights:
        adjusted = {
            name: weight * (1.2 if name == target else 1.0)
            for name, weight in weights.items()
        }
        total = sum(adjusted.values())
        yield {name: value / total for name, value in adjusted.items()}
        adjusted = {
            name: weight * (0.8 if name == target else 1.0)
            for name, weight in weights.items()
        }
        total = sum(adjusted.values())
        yield {name: value / total for name, value in adjusted.items()}


def compare_candidates(
    spec: BenchmarkSpec, evidence: list[CandidateEvidence]
) -> ComparisonResult:
    expected = {"native_runtime", "openai_agents_sdk", "pydanticai"}
    if {item.candidate for item in evidence} != expected:
        raise ValueError("comparison requires exactly the three declared candidates")
    weights = {item.name: item.weight for item in spec.criteria}
    scores = _score_with_weights(evidence, weights)
    winners = [
        _score_with_weights(evidence, scenario)[0].candidate
        for scenario in _sensitivity_weights(weights)
    ]
    selected = scores[0].candidate
    return ComparisonResult(
        benchmark_id=spec.benchmark_id,
        selected=selected,
        scores=scores,
        stable_under_sensitivity=set(winners) == {selected},
        sensitivity_winners=sorted(set(winners)),
        uncertainty=[
            "P95 measures local deterministic runtime overhead, not provider network latency.",
            "Scripted models isolate control semantics and do not compare model answer quality.",
            "The slice does not prove long-duration checkpoint or human-interrupt behavior.",
        ],
        rollback=[
            "Keep domain ResearchReport and tool contracts framework-neutral.",
            "Stop admitting new runs to the selected adapter.",
            "Export normalized state and allow in-flight runs to drain on their original adapter.",
            "Switch new runs to the previous adapter and replay the golden benchmark.",
        ],
    )


def render_adr(result: ComparisonResult, evidence: list[CandidateEvidence]) -> str:
    versions = ", ".join(f"{item.candidate}={item.framework_version}" for item in evidence)
    scores = "\n".join(f"  - {item.candidate}: {item.total:.4f}" for item in result.scores)
    rollback = "\n".join(f"  {index}. {step}" for index, step in enumerate(result.rollback, 1))
    uncertainty = "\n".join(f"  - {item}" for item in result.uncertainty)
    stability = "stable" if result.stable_under_sensitivity else "sensitive"
    return f"""# ADR-038: Research workflow runtime spike

- Status: Accepted for this bounded vertical slice
- Decision: `{result.selected}`
- Benchmark: `{result.benchmark_id}`
- Installed evidence: {versions}
- Sensitivity: {stability}; winners={', '.join(result.sensitivity_winners)}

## Weighted evidence

{scores}

## Uncertainty

{uncertainty}

## Rollback

{rollback}

## Review triggers

- long-running checkpoint or human approval becomes a hard requirement;
- P95 or cost proxy crosses the project budget;
- a pinned framework introduces a breaking change, license change, or security advisory.
"""
