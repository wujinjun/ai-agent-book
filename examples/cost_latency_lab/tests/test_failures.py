import math

import pytest

from cost_latency_lab.domain import (
    Budget,
    ModelProfile,
    Span,
    analyze_traces,
    choose_model,
)


def test_invalid_span_is_rejected() -> None:
    with pytest.raises(ValueError, match="interval"):
        Span("broken", 20, 10, 1)


def test_zero_success_never_reports_a_fake_finite_unit_cost() -> None:
    report = analyze_traces(())

    assert report.success_rate == 0
    assert math.isinf(report.cost_per_success_microunits)


def test_router_rejects_when_advanced_capability_exceeds_budget() -> None:
    decision = choose_model(
        (ModelProfile("large", "advanced", 900, 250, True),),
        required_capability="advanced",
        sensitive_data=True,
        budget=Budget(500, 200),
    )

    assert decision.status == "rejected"
    assert decision.model is None


def test_sensitive_data_cannot_route_to_disallowed_model() -> None:
    decision = choose_model(
        (ModelProfile("external", "advanced", 100, 50, False),),
        required_capability="advanced",
        sensitive_data=True,
        budget=Budget(500, 200),
    )

    assert decision.reason == "data_policy_rejected_all_models"
