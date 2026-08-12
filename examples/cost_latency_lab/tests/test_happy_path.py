from cost_latency_lab.domain import (
    Budget,
    CacheIdentity,
    ModelProfile,
    analyze_traces,
    cache_key,
    choose_model,
)
from cost_latency_lab.providers import OfflineTraceProvider


def test_trace_report_uses_wall_clock_and_cost_per_success() -> None:
    report = analyze_traces(OfflineTraceProvider().load())

    assert report.task_count == 3
    assert report.success_count == 2
    assert report.p95_wall_ms == 250
    assert report.total_cost_microunits == 2550
    assert report.cost_per_success_microunits == 1275
    assert report.retry_amplification == 4 / 3


def test_cache_key_is_stable_and_tenant_scoped() -> None:
    base = CacheIdentity("acme", "p1", "m1", "v1", "d1", {"query": "status"})

    assert cache_key(base) == cache_key(base)
    assert cache_key(base) != cache_key(
        CacheIdentity("other", "p1", "m1", "v1", "d1", {"query": "status"})
    )


def test_router_selects_lowest_cost_profile_that_meets_policy() -> None:
    decision = choose_model(
        (
            ModelProfile("small", "basic", 200, 80, True),
            ModelProfile("large", "advanced", 900, 250, True),
        ),
        required_capability="advanced",
        sensitive_data=True,
        budget=Budget(1_000, 300),
    )

    assert decision.model == "large"
    assert decision.status == "selected"

