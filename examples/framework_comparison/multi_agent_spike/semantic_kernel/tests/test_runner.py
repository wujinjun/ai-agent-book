import pytest
from runner import run


@pytest.mark.asyncio
async def test_plugins_approve_and_enforce_tool_policy() -> None:
    evidence = await run()
    assert evidence["task_success"] is True
    assert evidence["messages"] <= evidence["message_limit"]
    assert evidence["forbidden_tool_denied"] is True
    assert evidence["state_exported"] is True


@pytest.mark.asyncio
async def test_rejection_maps_to_budget_termination() -> None:
    evidence = await run(force_loop=True)
    assert evidence["task_success"] is False
    assert evidence["termination_reason"] == "budget_exhausted"
    assert evidence["messages"] <= evidence["message_limit"]
