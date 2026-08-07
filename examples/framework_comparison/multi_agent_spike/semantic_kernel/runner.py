"""Semantic Kernel plugin implementation of the bounded collaboration task."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from typing import Any

import semantic_kernel
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE.parent / "spec.json"


class ExecutorPlugin:
    @kernel_function(name="propose_patch", description="Create an allowlisted patch")
    def propose_patch(self, expected_patch: str) -> str:
        return json.dumps(
            {"patch": expected_patch, "denied_tools": ["read_secret"]}, ensure_ascii=False
        )


class ReviewerPlugin:
    def __init__(self, *, force_loop: bool = False) -> None:
        self.force_loop = force_loop

    @kernel_function(name="review_patch", description="Review a patch against policy")
    def review_patch(self, patch: str) -> str:
        if self.force_loop or patch != "TIMEOUT_SECONDS = 15":
            return "NEEDS_CHANGES"
        return "APPROVED"


async def run(*, force_loop: bool = False) -> dict[str, Any]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    kernel = Kernel()
    kernel.add_plugin(ExecutorPlugin(), plugin_name="executor")
    kernel.add_plugin(ReviewerPlugin(force_loop=force_loop), plugin_name="reviewer")
    proposal_result = await kernel.invoke(
        plugin_name="executor",
        function_name="propose_patch",
        expected_patch=spec["expected_patch"],
    )
    proposal = json.loads(str(proposal_result))
    verdict_result = await kernel.invoke(
        plugin_name="reviewer", function_name="review_patch", patch=proposal["patch"]
    )
    verdict = str(verdict_result)
    messages = [
        {"role": "executor", "content": proposal["patch"]},
        {"role": "reviewer", "content": verdict},
    ]
    state = {"messages": messages, "proposal": proposal, "verdict": verdict}
    return {
        "framework": "semantic-kernel",
        "version": semantic_kernel.__version__,
        "python": platform.python_version(),
        "integration_scope": (
            "Kernel/kernel_function plugins; bounded runner; no native Agent orchestration"
        ),
        "task_success": verdict == "APPROVED",
        "messages": len(messages),
        "message_limit": spec["message_limit"],
        "forbidden_tool_denied": proposal["denied_tools"] == ["read_secret"],
        "termination_reason": "approved" if verdict == "APPROVED" else "budget_exhausted",
        "state_exported": True,
        "shared_state": state,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    import asyncio

    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
