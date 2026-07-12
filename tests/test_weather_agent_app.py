import pytest

from ai_agent_book.apps.weather_agent import (
    ApprovalDecision,
    DeterministicPlanner,
    ToolAgent,
    ToolCall,
    ToolRegistry,
)


@pytest.mark.asyncio
async def test_multi_tool_loop_executes_weather_and_calculator() -> None:
    planner = DeterministicPlanner(
        [
            ToolCall(call_id="w1", name="get_weather", arguments={"city": "上海"}),
            ToolCall(call_id="c1", name="calculate", arguments={"expression": "26 * 9 / 5 + 32"}),
        ]
    )
    result = await ToolAgent(planner, ToolRegistry.default()).run("查天气并换算华氏温度")
    assert result.status == "completed"
    assert {item.name for item in result.observations} == {"get_weather", "calculate"}
    assert all(item.ok for item in result.observations)


@pytest.mark.asyncio
async def test_external_write_requires_matching_approval() -> None:
    call = ToolCall(
        call_id="a1",
        name="send_weather_alert",
        arguments={"recipient": "ops@example.test", "message": "暴雨"},
    )
    agent = ToolAgent(DeterministicPlanner([call]), ToolRegistry.default())
    blocked = await agent.run("发送告警")
    assert blocked.status == "approval_required"

    approved = await agent.run(
        "发送告警",
        approval=ApprovalDecision(call_id="a1", approved=True),
    )
    assert approved.status == "completed"
    assert approved.observations[0].result["delivery"] == "mock"


@pytest.mark.asyncio
async def test_invalid_tool_arguments_are_returned_as_observation() -> None:
    planner = DeterministicPlanner(
        [ToolCall(call_id="w1", name="get_weather", arguments={"city": ""})]
    )
    result = await ToolAgent(planner, ToolRegistry.default()).run("查天气")
    assert result.status == "failed"
    assert result.observations[0].ok is False
    assert "validation" in result.observations[0].error.lower()
