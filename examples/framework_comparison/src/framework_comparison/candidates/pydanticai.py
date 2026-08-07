"""PydanticAI candidate driven by FunctionModel in its isolated environment."""

import argparse
import asyncio
from time import perf_counter

import pydantic_ai
from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelResponse,
    ModelRetry,
    RunContext,
    ToolCallPart,
    models,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from framework_comparison.candidates.common import build_evidence
from framework_comparison.domain import ResearchReport
from framework_comparison.fixture import ResearchTools, TransientToolError, expected_report


async def execute_once() -> tuple[ResearchReport, ResearchTools, dict[str, object]]:
    tools = ResearchTools()
    agent = Agent(deps_type=ResearchTools, output_type=ResearchReport, retries=1)

    @agent.tool(retries=1)
    async def search_docs(ctx: RunContext[ResearchTools], query: str) -> list[str]:
        try:
            return await ctx.deps.search_docs(query)
        except TransientToolError as exc:
            raise ModelRetry("transient search; retry once") from exc

    @agent.tool
    async def read_doc(ctx: RunContext[ResearchTools], doc_id: str) -> str:
        return await ctx.deps.read_doc(doc_id)

    step = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        del messages
        nonlocal step
        step += 1
        if step <= 2:
            return ModelResponse(parts=[ToolCallPart("search_docs", {"query": "agent security"})])
        if step == 3:
            return ModelResponse(parts=[ToolCallPart("read_doc", {"doc_id": "D1"})])
        if step == 4:
            return ModelResponse(parts=[ToolCallPart("read_doc", {"doc_id": "D2"})])
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, expected_report().model_dump())]
        )

    with agent.override(model=FunctionModel(respond, model_name="comparison-fixture")):
        result = await agent.run("research agent security", deps=tools)
    state = {
        "message_count": len(result.all_messages()),
        "citations": result.output.citations,
        "search_attempts": tools.search_attempts,
    }
    return result.output, tools, state


async def run(runs: int) -> str:
    models.ALLOW_MODEL_REQUESTS = False
    latencies: list[float] = []
    final = None
    for _ in range(runs):
        started = perf_counter()
        final = await execute_once()
        latencies.append((perf_counter() - started) * 1000)
    assert final is not None
    report, tools, state = final
    evidence = build_evidence(
        candidate="pydanticai",
        framework_version=pydantic_ai.__version__,
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
