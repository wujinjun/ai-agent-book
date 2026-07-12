import asyncio
from typing import Any

from pydantic import BaseModel, Field

from ai_agent_book.tool_runtime import AgentStep, ToolDefinition, ToolRegistry, run_tool_loop


class AddArgs(BaseModel):
    left: int = Field(ge=0, le=1_000_000)
    right: int = Field(ge=0, le=1_000_000)


async def add(args: AddArgs) -> dict[str, int]:
    return {"value": args.left + args.right}


async def mock_decide(history: list[dict[str, Any]]) -> AgentStep:
    if not history:
        return AgentStep.tool_call("add", {"left": 20, "right": 22})
    value = history[-1]["result"]["value"]
    return AgentStep.final(f"20 + 22 = {value}")


async def main() -> None:
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="add", args_model=AddArgs, handler=add))
    answer = await run_tool_loop(mock_decide, registry, max_steps=3)
    print(f"最终回答：{answer}")


if __name__ == "__main__":
    asyncio.run(main())

