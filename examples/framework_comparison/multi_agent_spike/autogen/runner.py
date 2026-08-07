"""AutoGen AgentChat implementation of the bounded collaboration task."""

from __future__ import annotations

import hashlib
import json
import platform
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import autogen_agentchat
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import CancellationToken

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE.parent / "spec.json"


class DeterministicRole(BaseChatAgent):
    def __init__(self, name: str, *, force_loop: bool = False) -> None:
        super().__init__(name=name, description=f"Deterministic {name} role")
        self.force_loop = force_loop
        self.calls = 0
        self.denied_tools: list[str] = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        self.calls += 1
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        if self.name == "executor":
            self.denied_tools = ["read_secret"]
            content = f"PATCH {spec['expected_patch']}; DENIED read_secret"
        else:
            content = "NEEDS_CHANGES" if self.force_loop else "APPROVED"
        return Response(chat_message=TextMessage(content=content, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self.calls = 0
        self.denied_tools = []

    async def save_state(self) -> Mapping[str, Any]:
        return {"calls": self.calls, "denied_tools": self.denied_tools}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        self.calls = int(state["calls"])
        self.denied_tools = list(state["denied_tools"])

    async def close(self) -> None:
        return None


async def run(*, force_loop: bool = False) -> dict[str, Any]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    executor = DeterministicRole("executor")
    reviewer = DeterministicRole("reviewer", force_loop=force_loop)
    termination = TextMentionTermination("APPROVED") | MaxMessageTermination(spec["message_limit"])
    team = RoundRobinGroupChat(
        [executor, reviewer], termination_condition=termination, max_turns=spec["message_limit"]
    )
    result = await team.run(task=spec["request"])
    state = await team.save_state()
    role_messages = [m for m in result.messages if getattr(m, "source", "") != "user"]
    approved = any(getattr(m, "content", "") == "APPROVED" for m in role_messages)
    return {
        "framework": "autogen-agentchat",
        "version": autogen_agentchat.__version__,
        "python": platform.python_version(),
        "integration_scope": "BaseChatAgent/RoundRobinGroupChat/termination/state; no LLM",
        "task_success": approved,
        "messages": len(role_messages),
        "message_limit": spec["message_limit"],
        "forbidden_tool_denied": executor.denied_tools == ["read_secret"],
        "termination_reason": "approved" if approved else "budget_exhausted",
        "framework_stop_reason": result.stop_reason,
        "state_exported": bool(state.get("agent_states")),
        "shared_state": state,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    import asyncio

    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
