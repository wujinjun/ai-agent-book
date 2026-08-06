import asyncio
from collections.abc import Sequence

import pytest

from minimal_agent.domain import (
    AgentRuntime,
    BudgetExceeded,
    Cancelled,
    Decision,
    NoProgress,
    PolicyDenied,
    TerminationPolicy,
    ToolFailed,
)
from minimal_agent.providers import (
    DenyToolPolicy,
    FakeToolRegistry,
    InMemoryStateStore,
    ListTracer,
    ScriptedModelGateway,
)


def runtime_for(
    decisions: Sequence[Decision],
    tools: FakeToolRegistry | None = None,
    **termination: int,
) -> AgentRuntime:
    return AgentRuntime(
        model=ScriptedModelGateway(tuple(decisions)),
        tools=tools or FakeToolRegistry(),
        state_store=InMemoryStateStore(),
        tracer=ListTracer(),
        termination=TerminationPolicy(
            max_steps=termination.get("max_steps", 5),
            max_tokens=termination.get("max_tokens", 20),
            max_no_progress=termination.get("max_no_progress", 2),
        ),
    )


@pytest.mark.asyncio
async def test_unknown_tool_is_a_stable_runtime_failure() -> None:
    runtime = runtime_for((Decision.tool("missing", {}, tokens=1),))
    with pytest.raises(ToolFailed, match="unknown_tool"):
        await runtime.run("unknown", "call")


@pytest.mark.asyncio
async def test_tool_timeout_is_bounded() -> None:
    tools = FakeToolRegistry(results={"slow": "ok"}, delays={"slow": 0.05})
    runtime = runtime_for((Decision.tool("slow", {}, tokens=1),), tools=tools)
    runtime.tool_timeout_seconds = 0.001
    with pytest.raises(ToolFailed, match="timeout"):
        await runtime.run("timeout", "call")


@pytest.mark.asyncio
async def test_repeated_observation_stops_for_no_progress() -> None:
    repeated = Decision.tool("same", {}, tokens=1)
    runtime = runtime_for((repeated, repeated, repeated), max_no_progress=1)
    runtime.tools = FakeToolRegistry(results={"same": "unchanged"})
    with pytest.raises(NoProgress):
        await runtime.run("stuck", "call")


@pytest.mark.asyncio
async def test_cancellation_and_token_budget_are_enforced() -> None:
    cancelled = runtime_for((Decision.final("ignored", tokens=1),))
    cancelled.cancel()
    with pytest.raises(Cancelled):
        await cancelled.run("cancel", "stop")

    budgeted = runtime_for((Decision.final("too expensive", tokens=21),), max_tokens=20)
    with pytest.raises(BudgetExceeded):
        await budgeted.run("budget", "stop")

    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_policy_denies_tool_before_execution() -> None:
    tools = FakeToolRegistry(results={"delete": "deleted"})
    runtime = runtime_for((Decision.tool("delete", {"id": "1"}, tokens=1),), tools=tools)
    runtime.policy = DenyToolPolicy(frozenset({"delete"}))

    with pytest.raises(PolicyDenied, match="not_authorized"):
        await runtime.run("denied", "delete")

    assert tools.side_effect_count == 0
