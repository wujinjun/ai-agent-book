from pathlib import Path

import pytest
from agents import (
    Agent,
    RunConfig,
    Runner,
    SQLiteSession,
    function_tool,
    set_tracing_disabled,
)

from openai_agents_sdk_example.domain import SupportReport
from openai_agents_sdk_example.providers import ScriptedModel, function_call, message

set_tracing_disabled(True)


@function_tool
def add(a: int, b: int) -> int:
    """Add two fixture integers."""
    return a + b


@pytest.mark.asyncio
async def test_function_tool_and_structured_output_use_installed_sdk() -> None:
    model = ScriptedModel(
        (
            function_call("add", '{"a":2,"b":3}'),
            message('{"summary":"sum is 5","risk":"low"}', "message_2"),
        )
    )
    agent = Agent(name="calculator", model=model, tools=[add], output_type=SupportReport)

    result = await Runner.run(
        agent, "calculate", run_config=RunConfig(tracing_disabled=True), max_turns=3
    )

    assert result.final_output_as(SupportReport).summary == "sum is 5"
    assert [type(item).__name__ for item in result.new_items] == [
        "ToolCallItem",
        "ToolCallOutputItem",
        "MessageOutputItem",
    ]


@pytest.mark.asyncio
async def test_handoff_transfers_control_to_specialist() -> None:
    specialist = Agent(name="specialist", model=ScriptedModel((message("handled"),)))
    triage = Agent(
        name="triage",
        model=ScriptedModel((function_call("transfer_to_specialist", "{}"),)),
        handoffs=[specialist],
    )

    result = await Runner.run(
        triage, "route", run_config=RunConfig(tracing_disabled=True), max_turns=3
    )

    assert result.final_output == "handled"
    assert result.last_agent.name == "specialist"


@pytest.mark.asyncio
async def test_agent_as_tool_keeps_control_with_orchestrator() -> None:
    specialist = Agent(name="specialist", model=ScriptedModel((message("expert answer"),)))
    orchestrator = Agent(
        name="orchestrator",
        model=ScriptedModel(
            (
                function_call("consult_specialist", '{"input":"inspect incident"}'),
                message("orchestrated answer", "message_2"),
            )
        ),
        tools=[
            specialist.as_tool(
                tool_name="consult_specialist",
                tool_description="Ask the specialist while retaining orchestration control.",
                run_config=RunConfig(tracing_disabled=True),
                max_turns=2,
            )
        ],
    )

    result = await Runner.run(
        orchestrator,
        "investigate",
        run_config=RunConfig(tracing_disabled=True),
        max_turns=3,
    )

    assert result.final_output == "orchestrated answer"
    assert result.last_agent.name == "orchestrator"
    tool_outputs = [
        item for item in result.new_items if type(item).__name__ == "ToolCallOutputItem"
    ]
    assert tool_outputs
    assert "expert answer" in str(tool_outputs[0].output)


@pytest.mark.asyncio
async def test_sqlite_session_persists_run_items(tmp_path: Path) -> None:
    session = SQLiteSession("conversation-1", tmp_path / "session.db")
    agent = Agent(name="session-agent", model=ScriptedModel((message("remembered"),)))

    await Runner.run(
        agent,
        "hello",
        session=session,
        run_config=RunConfig(tracing_disabled=True),
    )

    items = await session.get_items()
    assert len(items) >= 2
    assert any(item.get("role") == "user" for item in items if isinstance(item, dict))
