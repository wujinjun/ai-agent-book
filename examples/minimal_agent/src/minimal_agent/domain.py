"""A small but recoverable Agent Runtime with explicit ports."""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Protocol


class RuntimeFailure(RuntimeError):
    pass


class ToolFailed(RuntimeFailure):
    pass


class BudgetExceeded(RuntimeFailure):
    pass


class NoProgress(RuntimeFailure):
    pass


class Cancelled(RuntimeFailure):
    pass


class PolicyDenied(RuntimeFailure):
    pass


@dataclass(frozen=True)
class Decision:
    kind: str
    tokens: int
    answer: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None

    @classmethod
    def final(cls, answer: str, *, tokens: int) -> "Decision":
        return cls("final", tokens, answer=answer)

    @classmethod
    def tool(cls, name: str, arguments: dict[str, Any], *, tokens: int) -> "Decision":
        return cls("tool", tokens, tool_name=name, arguments=arguments)


@dataclass(frozen=True)
class Observation:
    action_id: str
    tool_name: str
    result: Any


@dataclass
class RunState:
    run_id: str
    prompt: str
    version: int = 0
    status: str = "running"
    steps: int = 0
    tokens_used: int = 0
    no_progress_count: int = 0
    observations: list[Observation] = field(default_factory=list)
    answer: str | None = None


@dataclass(frozen=True)
class TerminationPolicy:
    max_steps: int
    max_tokens: int
    max_no_progress: int

    def __post_init__(self) -> None:
        if self.max_steps <= 0 or self.max_tokens <= 0 or self.max_no_progress <= 0:
            raise ValueError("TerminationPolicy 参数非法")


class ModelGateway(Protocol):
    async def decide(self, state: RunState) -> Decision: ...


class ToolRegistry(Protocol):
    async def execute(self, name: str, arguments: dict[str, Any], *, action_id: str) -> Any: ...


class StateStore(Protocol):
    async def load(self, run_id: str) -> RunState | None: ...

    async def save(self, state: RunState, *, expected_version: int) -> None: ...


class Policy(Protocol):
    def authorize(self, state: RunState, decision: Decision) -> None: ...


class Tracer(Protocol):
    def emit(self, event: str, attributes: dict[str, Any]) -> None: ...


def _action_id(state: RunState, decision: Decision) -> str:
    payload = json.dumps(
        {
            "run_id": state.run_id,
            "step": state.steps,
            "tool": decision.tool_name,
            "arguments": decision.arguments,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


class AgentRuntime:
    def __init__(
        self,
        *,
        model: ModelGateway,
        tools: ToolRegistry,
        state_store: StateStore,
        tracer: Tracer,
        termination: TerminationPolicy,
        policy: Policy | None = None,
        tool_timeout_seconds: float = 1.0,
        crash_after_tool_once: bool = False,
    ) -> None:
        from minimal_agent.providers import AllowAllPolicy

        self.model = model
        self.tools = tools
        self.state_store = state_store
        self.tracer = tracer
        self.termination = termination
        self.policy = policy or AllowAllPolicy()
        self.tool_timeout_seconds = tool_timeout_seconds
        self.crash_after_tool_once = crash_after_tool_once
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def run(self, run_id: str, prompt: str) -> RunState:
        state = await self.state_store.load(run_id)
        if state is None:
            state = RunState(run_id=run_id, prompt=prompt)
            await self.state_store.save(state, expected_version=0)

        while state.status == "running":
            self._check_before_step(state)
            decision = await self.model.decide(state)
            if decision.tokens < 0:
                raise RuntimeFailure("invalid_token_usage")
            state.tokens_used += decision.tokens
            if state.tokens_used > self.termination.max_tokens:
                raise BudgetExceeded("token_budget_exceeded")
            if decision.kind == "final":
                if not decision.answer:
                    raise RuntimeFailure("empty_final_answer")
                state.answer = decision.answer
                state.status = "completed"
                await self._commit(state)
                self.tracer.emit("run.completed", {"run_id": run_id, "steps": state.steps})
                return state
            if decision.kind != "tool" or not decision.tool_name or decision.arguments is None:
                raise RuntimeFailure("invalid_decision")

            self.policy.authorize(state, decision)
            action_id = _action_id(state, decision)
            try:
                result = await asyncio.wait_for(
                    self.tools.execute(
                        decision.tool_name, decision.arguments, action_id=action_id
                    ),
                    timeout=self.tool_timeout_seconds,
                )
            except TimeoutError as error:
                raise ToolFailed("tool_timeout") from error
            except ToolFailed:
                raise
            except Exception as error:
                raise ToolFailed("tool_execution_failed") from error

            if self.crash_after_tool_once:
                self.crash_after_tool_once = False
                raise RuntimeError("simulated crash after confirmed tool result")

            previous = state.observations[-1].result if state.observations else object()
            state.no_progress_count = (
                state.no_progress_count + 1 if result == previous else 0
            )
            state.observations.append(Observation(action_id, decision.tool_name, result))
            state.steps += 1
            await self._commit(state)
            self.tracer.emit(
                "tool.completed",
                {"run_id": run_id, "tool": decision.tool_name, "action_id": action_id},
            )
            if state.no_progress_count >= self.termination.max_no_progress:
                raise NoProgress("no_progress")

        return state

    def _check_before_step(self, state: RunState) -> None:
        if self._cancelled:
            raise Cancelled("run_cancelled")
        if state.steps >= self.termination.max_steps:
            raise BudgetExceeded("step_budget_exceeded")

    async def _commit(self, state: RunState) -> None:
        expected = state.version
        state.version += 1
        await self.state_store.save(state, expected_version=expected)
