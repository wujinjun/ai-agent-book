"""Run the recoverable offline minimal Agent fixture."""

import argparse
import asyncio
import json

from minimal_agent.domain import AgentRuntime, Decision, TerminationPolicy
from minimal_agent.providers import (
    FakeToolRegistry,
    InMemoryStateStore,
    ListTracer,
    ScriptedModelGateway,
)


async def run_fixture() -> dict[str, object]:
    tools = FakeToolRegistry(results={"lookup": {"budget": 16}})
    tracer = ListTracer()
    runtime = AgentRuntime(
        model=ScriptedModelGateway(
            (
                Decision.tool("lookup", {"query": "budget"}, tokens=2),
                Decision.final("budget is 16", tokens=3),
            )
        ),
        tools=tools,
        state_store=InMemoryStateStore(),
        tracer=tracer,
        termination=TerminationPolicy(max_steps=4, max_tokens=20, max_no_progress=2),
    )
    state = await runtime.run("demo", "find budget")
    return {
        "status": state.status,
        "answer": state.answer,
        "steps": state.steps,
        "tokens_used": state.tokens_used,
        "side_effect_count": tools.side_effect_count,
        "trace_events": [name for name, _ in tracer.events],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("recoverable",), default="recoverable")
    args = parser.parse_args()
    del args
    print(json.dumps(asyncio.run(run_fixture()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
