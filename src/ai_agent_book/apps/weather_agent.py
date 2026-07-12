"""项目 2：多工具、参数校验、并行执行和人工批准的 Tool Loop。"""

from __future__ import annotations

import ast
import asyncio
import operator
from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError

from ai_agent_book.project_domains import WeatherService


class ToolCall(BaseModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class ApprovalDecision(BaseModel):
    call_id: str
    approved: bool


class ToolObservation(BaseModel):
    call_id: str
    name: str
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class AgentResult(BaseModel):
    status: Literal["completed", "approval_required", "failed"]
    observations: list[ToolObservation]
    pending_calls: list[ToolCall] = Field(default_factory=list)


class Planner(Protocol):
    async def plan(self, prompt: str) -> list[ToolCall]: ...


class DeterministicPlanner:
    """测试和无密钥演示用 Planner；在线模型只需实现相同协议。"""

    def __init__(self, calls: list[ToolCall]) -> None:
        self.calls = calls

    async def plan(self, prompt: str) -> list[ToolCall]:
        if not prompt.strip():
            raise ValueError("prompt 不能为空")
        return self.calls


class WeatherArguments(BaseModel):
    city: str = Field(min_length=1, max_length=80)


class CalculatorArguments(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


class AlertArguments(BaseModel):
    recipient: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    message: str = Field(min_length=1, max_length=1_000)


ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ToolSpec(BaseModel):
    name: str
    risk: Literal["read", "external_write"]
    schema_model: type[BaseModel]
    handler: ToolHandler

    model_config = {"arbitrary_types_allowed": True}


_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _calculate(expression: str) -> float:
    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            return _OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
        raise ValueError("只允许数字和 + - * / 运算")

    return evaluate(ast.parse(expression, mode="eval"))


class ToolRegistry:
    def __init__(self, specs: list[ToolSpec]) -> None:
        self.specs = {spec.name: spec for spec in specs}

    @classmethod
    def default(cls) -> ToolRegistry:
        weather = WeatherService(failures_before_success=1)

        async def get_weather(arguments: dict[str, Any]) -> dict[str, Any]:
            parsed = WeatherArguments.model_validate(arguments)
            return (await weather.get_weather(parsed.city)).model_dump()

        async def calculate(arguments: dict[str, Any]) -> dict[str, Any]:
            parsed = CalculatorArguments.model_validate(arguments)
            return {"value": _calculate(parsed.expression)}

        async def send_alert(arguments: dict[str, Any]) -> dict[str, Any]:
            parsed = AlertArguments.model_validate(arguments)
            return {
                "delivery": "mock",
                "recipient": parsed.recipient,
                "message": parsed.message,
            }

        return cls(
            [
                ToolSpec(
                    name="get_weather",
                    risk="read",
                    schema_model=WeatherArguments,
                    handler=get_weather,
                ),
                ToolSpec(
                    name="calculate",
                    risk="read",
                    schema_model=CalculatorArguments,
                    handler=calculate,
                ),
                ToolSpec(
                    name="send_weather_alert",
                    risk="external_write",
                    schema_model=AlertArguments,
                    handler=send_alert,
                ),
            ]
        )

    async def execute(self, call: ToolCall) -> ToolObservation:
        spec = self.specs.get(call.name)
        if spec is None:
            return ToolObservation(
                call_id=call.call_id,
                name=call.name,
                ok=False,
                error="unknown tool",
            )
        try:
            validated = spec.schema_model.model_validate(call.arguments)
            result = await asyncio.wait_for(spec.handler(validated.model_dump()), timeout=3)
            return ToolObservation(
                call_id=call.call_id,
                name=call.name,
                ok=True,
                result=result,
            )
        except ValidationError as exc:
            return ToolObservation(
                call_id=call.call_id,
                name=call.name,
                ok=False,
                error=f"validation error: {exc.error_count()} issue(s)",
            )
        except (TimeoutError, ValueError, ZeroDivisionError) as exc:
            return ToolObservation(
                call_id=call.call_id,
                name=call.name,
                ok=False,
                error=f"tool error: {type(exc).__name__}",
            )


class ToolAgent:
    def __init__(self, planner: Planner, registry: ToolRegistry, *, max_calls: int = 8) -> None:
        self.planner = planner
        self.registry = registry
        self.max_calls = max_calls

    async def run(
        self,
        prompt: str,
        *,
        approval: ApprovalDecision | None = None,
    ) -> AgentResult:
        calls = await self.planner.plan(prompt)
        if len(calls) > self.max_calls:
            return AgentResult(status="failed", observations=[])
        pending = [
            call
            for call in calls
            if self.registry.specs.get(call.name)
            and self.registry.specs[call.name].risk == "external_write"
            and not (approval and approval.call_id == call.call_id and approval.approved)
        ]
        if pending:
            return AgentResult(
                status="approval_required",
                observations=[],
                pending_calls=pending,
            )
        observations = list(await asyncio.gather(*(self.registry.execute(call) for call in calls)))
        status: Literal["completed", "failed"] = (
            "completed" if all(observation.ok for observation in observations) else "failed"
        )
        return AgentResult(status=status, observations=observations)
