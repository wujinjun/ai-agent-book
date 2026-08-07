"""Native Python candidate with an explicit deterministic control loop."""

import argparse
import asyncio
from time import perf_counter

from framework_comparison.candidates.common import build_evidence
from framework_comparison.domain import ResearchReport
from framework_comparison.fixture import ResearchTools, TransientToolError, expected_report


async def execute_once() -> tuple[ResearchReport, ResearchTools, dict[str, object]]:
    tools = ResearchTools()
    try:
        await tools.search_docs("agent security")
    except TransientToolError:
        await tools.search_docs("agent security")
    await tools.read_doc("D1")
    await tools.read_doc("D2")
    report = expected_report()
    state = {
        "status": "completed",
        "citations": report.citations,
        "search_attempts": tools.search_attempts,
        "events": [event.model_dump() for event in tools.events],
    }
    return report, tools, state


async def run(runs: int) -> str:
    latencies: list[float] = []
    final = None
    for _ in range(runs):
        started = perf_counter()
        final = await execute_once()
        latencies.append((perf_counter() - started) * 1000)
    assert final is not None
    report, tools, state = final
    evidence = build_evidence(
        candidate="native_runtime",
        framework_version="stdlib",
        report=report,
        events=tools.events,
        latencies_ms=latencies,
        model_requests=4,
        state_export=state,
        implementation_file=__file__,
    )
    return evidence.model_dump_json(indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args()
    print(asyncio.run(run(args.runs)))


if __name__ == "__main__":
    main()
