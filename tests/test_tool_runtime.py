import asyncio
from typing import Any

import pytest
from pydantic import BaseModel, Field

from ai_agent_book.tool_runtime import (
    AgentStep,
    ToolDefinition,
    ToolRegistry,
    ToolRuntimeError,
    run_tool_loop,
)


class AddArgs(BaseModel):
    left: int = Field(ge=0)
    right: int = Field(ge=0)


async def add(args: AddArgs) -> dict[str, int]:
    return {"value": args.left + args.right}


@pytest.fixture
def registry() -> ToolRegistry:
    tools = ToolRegistry()
    tools.register(ToolDefinition(name="add", args_model=AddArgs, handler=add))
    return tools


@pytest.mark.asyncio
async def test_registry_validates_arguments_before_execution(registry: ToolRegistry) -> None:
    with pytest.raises(ToolRuntimeError, match="参数校验失败"):
        await registry.execute("add", {"left": -1, "right": 2})


@pytest.mark.asyncio
async def test_registry_rejects_unknown_tool(registry: ToolRegistry) -> None:
    with pytest.raises(ToolRuntimeError, match="未知工具"):
        await registry.execute("delete_everything", {})


@pytest.mark.asyncio
async def test_registry_enforces_tool_timeout() -> None:
    async def slow_add(args: AddArgs) -> dict[str, int]:
        await asyncio.sleep(0.05)
        return {"value": args.left + args.right}

    tools = ToolRegistry()
    tools.register(
        ToolDefinition(
            name="slow_add",
            args_model=AddArgs,
            handler=slow_add,
            timeout_seconds=0.001,
        )
    )

    with pytest.raises(ToolRuntimeError, match="执行超时"):
        await tools.execute("slow_add", {"left": 1, "right": 2})


@pytest.mark.asyncio
async def test_tool_loop_returns_final_answer_after_observation(registry: ToolRegistry) -> None:
    observations: list[dict[str, Any]] = []

    async def decide(history: list[dict[str, Any]]) -> AgentStep:
        observations[:] = history
        if not history:
            return AgentStep.tool_call("add", {"left": 20, "right": 22})
        return AgentStep.final("结果是 42")

    result = await run_tool_loop(decide, registry, max_steps=3)

    assert result == "结果是 42"
    assert observations == [{"tool": "add", "result": {"value": 42}}]


@pytest.mark.asyncio
async def test_tool_loop_stops_at_configured_limit(registry: ToolRegistry) -> None:
    async def always_call(_: list[dict[str, Any]]) -> AgentStep:
        return AgentStep.tool_call("add", {"left": 1, "right": 1})

    with pytest.raises(ToolRuntimeError, match="超过最大步数 2"):
        await run_tool_loop(always_call, registry, max_steps=2)
