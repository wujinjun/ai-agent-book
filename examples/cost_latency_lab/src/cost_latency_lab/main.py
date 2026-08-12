"""Print a deterministic cost and latency report."""

import argparse
import json
from dataclasses import asdict

from cost_latency_lab.domain import Budget, ModelProfile, analyze_traces, choose_model
from cost_latency_lab.providers import OfflineTraceProvider


def build_report() -> dict[str, object]:
    traces = OfflineTraceProvider().load()
    report = analyze_traces(traces)
    route = choose_model(
        (
            ModelProfile("small", "basic", 200, 80, True),
            ModelProfile("large", "advanced", 900, 250, True),
        ),
        required_capability="advanced",
        sensitive_data=True,
        budget=Budget(max_cost_microunits=1_000, max_wall_ms=300),
    )
    return {"trace_report": asdict(report), "route": asdict(route)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("baseline",), default="baseline")
    parser.parse_args()
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

