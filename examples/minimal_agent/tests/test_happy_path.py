import pytest

from minimal_agent.domain import AgentRuntime, Decision, TerminationPolicy
from minimal_agent.providers import (
    FakeToolRegistry,
    InMemoryStateStore,
    ListTracer,
    ScriptedModelGateway,
)


@pytest.mark.asyncio
async def test_direct_answer_finishes_without_tool_call() -> None:
    runtime = AgentRuntime(
        model=ScriptedModelGateway((Decision.final("done", tokens=3),)),
        tools=FakeToolRegistry(),
        state_store=InMemoryStateStore(),
        tracer=ListTracer(),
        termination=TerminationPolicy(max_steps=4, max_tokens=20, max_no_progress=2),
    )

    result = await runtime.run("direct", "answer directly")

    assert result.answer == "done"
    assert result.status == "completed"
    assert result.tokens_used == 3


@pytest.mark.asyncio
async def test_tool_observation_is_visible_to_next_model_step() -> None:
    model = ScriptedModelGateway(
        (
            Decision.tool("lookup", {"query": "budget"}, tokens=2),
            Decision.final("found", tokens=2),
        )
    )
    tools = FakeToolRegistry(results={"lookup": {"value": 16}})
    runtime = AgentRuntime(
        model=model,
        tools=tools,
        state_store=InMemoryStateStore(),
        tracer=ListTracer(),
        termination=TerminationPolicy(max_steps=4, max_tokens=20, max_no_progress=2),
    )

    result = await runtime.run("tool", "find budget")

    assert result.answer == "found"
    assert model.seen_states[-1].observations[-1].result == {"value": 16}
    assert tools.side_effect_count == 1


@pytest.mark.asyncio
async def test_restart_does_not_replay_confirmed_side_effect() -> None:
    store = InMemoryStateStore()
    tools = FakeToolRegistry(results={"send": {"receipt": "r-1"}})
    model = ScriptedModelGateway(
        (
            Decision.tool("send", {"message": "hello"}, tokens=1),
            Decision.final("sent", tokens=1),
        )
    )
    runtime = AgentRuntime(
        model=model,
        tools=tools,
        state_store=store,
        tracer=ListTracer(),
        termination=TerminationPolicy(max_steps=4, max_tokens=20, max_no_progress=2),
        crash_after_tool_once=True,
    )

    with pytest.raises(RuntimeError, match="simulated crash"):
        await runtime.run("recover", "send")

    recovered = await AgentRuntime(
        model=model,
        tools=tools,
        state_store=store,
        tracer=ListTracer(),
        termination=TerminationPolicy(max_steps=4, max_tokens=20, max_no_progress=2),
    ).run("recover", "send")

    assert recovered.answer == "sent"
    assert tools.side_effect_count == 1
