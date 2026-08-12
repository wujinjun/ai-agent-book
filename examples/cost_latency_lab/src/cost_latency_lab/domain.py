"""Provider-neutral task economics, critical-path and routing rules."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Span:
    name: str
    start_ms: int
    end_ms: int
    cost_microunits: int
    logical_call_id: str | None = None
    attempt: int = 1

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.end_ms < self.start_ms:
            raise ValueError("invalid span interval")
        if self.cost_microunits < 0 or self.attempt < 1:
            raise ValueError("invalid span cost or attempt")

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass(frozen=True, slots=True)
class TaskTrace:
    task_id: str
    success: bool
    spans: tuple[Span, ...]

    @property
    def wall_ms(self) -> int:
        if not self.spans:
            return 0
        return max(span.end_ms for span in self.spans) - min(
            span.start_ms for span in self.spans
        )

    @property
    def total_cost_microunits(self) -> int:
        return sum(span.cost_microunits for span in self.spans)


@dataclass(frozen=True, slots=True)
class TraceReport:
    task_count: int
    success_count: int
    success_rate: float
    p95_wall_ms: int
    total_cost_microunits: int
    cost_per_success_microunits: float
    physical_attempts: int
    logical_calls: int
    retry_amplification: float


def _nearest_rank(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def analyze_traces(traces: tuple[TaskTrace, ...]) -> TraceReport:
    success_count = sum(trace.success for trace in traces)
    total_cost = sum(trace.total_cost_microunits for trace in traces)
    calls = [
        span
        for trace in traces
        for span in trace.spans
        if span.logical_call_id is not None
    ]
    logical_calls = len(
        {
            (trace.task_id, span.logical_call_id)
            for trace in traces
            for span in trace.spans
            if span.logical_call_id is not None
        }
    )
    return TraceReport(
        task_count=len(traces),
        success_count=success_count,
        success_rate=success_count / len(traces) if traces else 0.0,
        p95_wall_ms=_nearest_rank([trace.wall_ms for trace in traces], 0.95),
        total_cost_microunits=total_cost,
        cost_per_success_microunits=(total_cost / success_count if success_count else math.inf),
        physical_attempts=len(calls),
        logical_calls=logical_calls,
        retry_amplification=(len(calls) / logical_calls if logical_calls else 1.0),
    )


@dataclass(frozen=True, slots=True)
class CacheIdentity:
    tenant_id: str
    permission_version: str
    model_version: str
    prompt_version: str
    data_version: str
    request: dict[str, object]


def cache_key(identity: CacheIdentity) -> str:
    payload = json.dumps(
        {
            "tenant_id": identity.tenant_id,
            "permission_version": identity.permission_version,
            "model_version": identity.model_version,
            "prompt_version": identity.prompt_version,
            "data_version": identity.data_version,
            "request": identity.request,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Budget:
    max_cost_microunits: int
    max_wall_ms: int


@dataclass(frozen=True, slots=True)
class ModelProfile:
    name: str
    capability: Literal["basic", "advanced"]
    estimated_cost_microunits: int
    estimated_wall_ms: int
    allowed_for_sensitive_data: bool


@dataclass(frozen=True, slots=True)
class RouteDecision:
    status: Literal["selected", "degraded", "rejected"]
    model: str | None
    reason: str


def choose_model(
    profiles: tuple[ModelProfile, ...],
    *,
    required_capability: Literal["basic", "advanced"],
    sensitive_data: bool,
    budget: Budget,
) -> RouteDecision:
    rank = {"basic": 0, "advanced": 1}
    capable = [
        profile
        for profile in profiles
        if rank[profile.capability] >= rank[required_capability]
    ]
    eligible = [
        profile
        for profile in capable
        if not sensitive_data or profile.allowed_for_sensitive_data
    ]
    if capable and not eligible:
        return RouteDecision("rejected", None, "data_policy_rejected_all_models")
    within_budget = [
        profile
        for profile in eligible
        if profile.estimated_cost_microunits <= budget.max_cost_microunits
        and profile.estimated_wall_ms <= budget.max_wall_ms
    ]
    if within_budget:
        selected = min(
            within_budget,
            key=lambda profile: (profile.estimated_cost_microunits, profile.estimated_wall_ms),
        )
        return RouteDecision("selected", selected.name, "capability_policy_and_budget_satisfied")
    return RouteDecision("rejected", None, "no_allowed_model_within_budget")
