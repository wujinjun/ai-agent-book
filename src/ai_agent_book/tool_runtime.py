"""一个刻意保持很小、但保留生产边界的异步工具调用运行时。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError


class ToolRuntimeError(RuntimeError):
    """运行时拒绝继续执行时抛出的可预期错误。"""


ToolHandler = Callable[[Any], Awaitable[Any]]
DecisionFunction = Callable[[list[dict[str, Any]]], Awaitable["AgentStep"]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    args_model: type[BaseModel]
    handler: ToolHandler
    timeout_seconds: float = 10.0


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if not definition.name:
            raise ValueError("工具名不能为空")
        if definition.timeout_seconds <= 0:
            raise ValueError("工具超时必须大于 0")
        if definition.name in self._tools:
            raise ValueError(f"工具已注册: {definition.name}")
        self._tools[definition.name] = definition

    async def execute(self, name: str, raw_arguments: dict[str, Any]) -> Any:
        import asyncio

        definition = self._tools.get(name)
        if definition is None:
            raise ToolRuntimeError(f"未知工具: {name}")
        try:
            arguments = definition.args_model.model_validate(raw_arguments)
        except ValidationError as exc:
            raise ToolRuntimeError(f"工具 {name} 参数校验失败: {exc}") from exc

        try:
            return await asyncio.wait_for(
                definition.handler(arguments), timeout=definition.timeout_seconds
            )
        # Python 3.12 将 asyncio.TimeoutError 设为内置 TimeoutError 的别名；
        # 教材 CI 仍兼容部分 3.9 环境，因此这里同时捕获两者。
        except (TimeoutError, asyncio.TimeoutError) as exc:  # noqa: UP041
            raise ToolRuntimeError(f"工具 {name} 执行超时") from exc
        except ToolRuntimeError:
            raise
        except Exception as exc:
            raise ToolRuntimeError(f"工具 {name} 执行失败: {exc}") from exc


@dataclass(frozen=True)
class AgentStep:
    kind: str
    name: str | None = None
    arguments: dict[str, Any] | None = None
    answer: str | None = None

    @classmethod
    def tool_call(cls, name: str, arguments: dict[str, Any]) -> AgentStep:
        return cls(kind="tool_call", name=name, arguments=arguments)

    @classmethod
    def final(cls, answer: str) -> AgentStep:
        return cls(kind="final", answer=answer)


async def run_tool_loop(
    decide: DecisionFunction,
    registry: ToolRegistry,
    *,
    max_steps: int,
) -> str:
    if max_steps <= 0:
        raise ValueError("max_steps 必须大于 0")

    history: list[dict[str, Any]] = []
    for _ in range(max_steps):
        step = await decide(history.copy())
        if step.kind == "final":
            if step.answer is None:
                raise ToolRuntimeError("最终回答不能为空")
            return step.answer
        if step.kind != "tool_call" or step.name is None or step.arguments is None:
            raise ToolRuntimeError(f"无效 Agent 步骤: {step.kind}")
        result = await registry.execute(step.name, step.arguments)
        history.append({"tool": step.name, "result": result})

    raise ToolRuntimeError(f"Agent 超过最大步数 {max_steps}")
