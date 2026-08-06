"""Deterministic adapters for testing the Agent Runtime offline."""

import asyncio
import copy
from dataclasses import dataclass, field
from typing import Any

from minimal_agent.domain import Decision, PolicyDenied, RunState, ToolFailed


@dataclass
class ScriptedModelGateway:
    decisions: tuple[Decision, ...]
    seen_states: list[RunState] = field(default_factory=list, init=False)

    async def decide(self, state: RunState) -> Decision:
        self.seen_states.append(copy.deepcopy(state))
        return self.decisions[min(state.steps, len(self.decisions) - 1)]


@dataclass
class FakeToolRegistry:
    results: dict[str, Any] = field(default_factory=dict)
    delays: dict[str, float] = field(default_factory=dict)
    side_effect_count: int = field(default=0, init=False)
    _receipts: dict[str, Any] = field(default_factory=dict, init=False)

    async def execute(self, name: str, arguments: dict[str, Any], *, action_id: str) -> Any:
        del arguments
        if action_id in self._receipts:
            return copy.deepcopy(self._receipts[action_id])
        if name not in self.results:
            raise ToolFailed("unknown_tool")
        if delay := self.delays.get(name):
            await asyncio.sleep(delay)
        result = copy.deepcopy(self.results[name])
        self.side_effect_count += 1
        self._receipts[action_id] = result
        return copy.deepcopy(result)


class InMemoryStateStore:
    def __init__(self) -> None:
        self._states: dict[str, RunState] = {}

    async def load(self, run_id: str) -> RunState | None:
        state = self._states.get(run_id)
        return copy.deepcopy(state) if state is not None else None

    async def save(self, state: RunState, *, expected_version: int) -> None:
        current = self._states.get(state.run_id)
        current_version = current.version if current is not None else 0
        if current_version != expected_version:
            raise RuntimeError("checkpoint_version_conflict")
        self._states[state.run_id] = copy.deepcopy(state)


class AllowAllPolicy:
    def authorize(self, state: RunState, decision: Decision) -> None:
        del state, decision


@dataclass(frozen=True)
class DenyToolPolicy:
    denied_tools: frozenset[str]

    def authorize(self, state: RunState, decision: Decision) -> None:
        del state
        if decision.tool_name in self.denied_tools:
            raise PolicyDenied("tool_not_authorized")


@dataclass
class ListTracer:
    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def emit(self, event: str, attributes: dict[str, Any]) -> None:
        self.events.append((event, copy.deepcopy(attributes)))
