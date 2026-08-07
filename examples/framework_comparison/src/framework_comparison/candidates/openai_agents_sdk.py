"""OpenAI Agents SDK candidate driven by the installed SDK and a scripted model."""

import argparse
import asyncio
import json
from time import perf_counter

import agents
from agents import Agent, RunConfig, Runner, function_tool, set_tracing_disabled
from openai_agents_sdk_example.providers import ScriptedModel, function_call, message

from framework_comparison.candidates.common import build_evidence
from framework_comparison.domain import ResearchReport
from framework_comparison.fixture import ResearchTools, TransientToolError, expected_report


async def execute_once() -> tuple[ResearchReport, ResearchTools, dict[str, object]]:
    tools = ResearchTools()

    @function_tool
    async def search_docs(query: str) -> str:
        """Search the fixed benchmark corpus."""
        try:
            return json.dumps(await tools.search_docs(query))
        except TransientToolError:
            return json.dumps({"error": "transient_search"})

    @function_tool
    async def read_doc(doc_id: str) -> str:
        """Read an allowed benchmark document."""
        return await tools.read_doc(doc_id)

    expected = expected_report()
    model = ScriptedModel(
        (
            function_call("search_docs", '{"query":"agent security"}', call_id="search-1"),
            function_call("search_docs", '{"query":"agent security"}', call_id="search-2"),
            function_call("read_doc", '{"doc_id":"D1"}', call_id="read-1"),
            function_call("read_doc", '{"doc_id":"D2"}', call_id="read-2"),
            message(expected.model_dump_json(), "final-message"),
        )
    )
    agent = Agent(
        name="research benchmark",
        model=model,
        tools=[search_docs, read_doc],
        output_type=ResearchReport,
    )
    result = await Runner.run(
        agent,
        "research agent security",
        max_turns=6,
        run_config=RunConfig(tracing_disabled=True, trace_include_sensitive_data=False),
    )
    report = result.final_output_as(ResearchReport)
    state: dict[str, object] = {
        "last_agent": result.last_agent.name,
        "items": [type(item).__name__ for item in result.new_items],
        "citations": report.citations,
    }
    return report, tools, state


async def run(runs: int) -> str:
    set_tracing_disabled(True)
    latencies: list[float] = []
    final = None
    for _ in range(runs):
        started = perf_counter()
        final = await execute_once()
        latencies.append((perf_counter() - started) * 1000)
    assert final is not None
    report, tools, state = final
    evidence = build_evidence(
        candidate="openai_agents_sdk",
        framework_version=agents.__version__,
        report=report,
        events=tools.events,
        latencies_ms=latencies,
        model_requests=5,
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
