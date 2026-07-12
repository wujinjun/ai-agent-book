import pytest

from ai_agent_book.apps.weather_agent import DeterministicPlanner, ToolAgent, ToolCall, ToolRegistry


@pytest.mark.asyncio
async def test_weather_tool_loop() -> None:
    planner = DeterministicPlanner(
        [ToolCall(call_id="w", name="get_weather", arguments={"city": "上海"})]
    )
    result = await ToolAgent(planner, ToolRegistry.default()).run("weather")
    assert result.status == "completed"
