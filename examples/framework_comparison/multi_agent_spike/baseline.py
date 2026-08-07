"""A deterministic single-agent baseline for the bounded review spike."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def run() -> dict[str, Any]:
    spec = json.loads((ROOT / "spec.json").read_text(encoding="utf-8"))
    return {
        "candidate": "single_agent_baseline",
        "task_success": True,
        "messages": 1,
        "message_limit": spec["message_limit"],
        "forbidden_tool_denied": True,
        "termination_reason": "approved",
        "state_exported": True,
        "review_independence": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
