import pytest
from runner import run


@pytest.mark.asyncio
async def test_team_approves_with_exported_state_and_denied_secret() -> None:
    evidence = await run()
    assert evidence["task_success"] is True
    assert evidence["messages"] <= evidence["message_limit"]
    assert evidence["forbidden_tool_denied"] is True
    assert evidence["state_exported"] is True


@pytest.mark.asyncio
async def test_loop_stops_at_message_budget() -> None:
    evidence = await run(force_loop=True)
    assert evidence["task_success"] is False
    assert evidence["termination_reason"] == "budget_exhausted"
    assert evidence["messages"] <= evidence["message_limit"]
