"""CrewAI Flow implementation of the bounded Reviewer/Executor task."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any

import crewai
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE.parent / "spec.json"


class ReviewState(BaseModel):
    messages: list[dict[str, str]] = Field(default_factory=list)
    denied_tools: list[str] = Field(default_factory=list)
    patch: str = ""
    termination_reason: str = "running"
    force_loop: bool = False


class ReviewFlow(Flow[ReviewState]):
    @start()
    def executor(self) -> str:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        if "read_secret" in spec["forbidden_tools"]:
            self.state.denied_tools.append("read_secret")
        self.state.patch = spec["expected_patch"]
        self.state.messages.append({"role": "executor", "content": self.state.patch})
        return self.state.patch

    @listen(executor)
    def reviewer(self, patch: str) -> str:
        verdict = "NEEDS_CHANGES" if self.state.force_loop else "APPROVED"
        if patch != "TIMEOUT_SECONDS = 15":
            verdict = "NEEDS_CHANGES"
        self.state.messages.append({"role": "reviewer", "content": verdict})
        self.state.termination_reason = "approved" if verdict == "APPROVED" else "budget_exhausted"
        return verdict


def run(*, force_loop: bool = False) -> dict[str, Any]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    flow = ReviewFlow(
        initial_state=ReviewState(force_loop=force_loop),
        suppress_flow_events=True,
        tracing=False,
        max_method_calls=spec["message_limit"],
    )
    flow.kickoff()
    state = flow.state.model_dump()
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "framework": "crewai",
        "version": crewai.__version__,
        "python": platform.python_version(),
        "integration_scope": "Flow state/start/listen; deterministic roles; no LLM",
        "task_success": state["termination_reason"] == "approved",
        "messages": len(state["messages"]),
        "message_limit": spec["message_limit"],
        "forbidden_tool_denied": state["denied_tools"] == ["read_secret"],
        "termination_reason": state["termination_reason"],
        "state_exported": bool(state["messages"]),
        "shared_state": state,
        "source_sha256": source_hash,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
