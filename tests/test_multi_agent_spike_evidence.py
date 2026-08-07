from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "examples" / "framework_comparison" / "multi_agent_spike"


def test_committed_multi_agent_evidence_matches_sources_and_contract() -> None:
    evidence = json.loads((SPIKE / "evidence.json").read_text(encoding="utf-8"))
    folders = {
        "crewai": "crewai",
        "autogen-agentchat": "autogen",
        "semantic-kernel": "semantic_kernel",
    }
    assert evidence["python"].startswith("3.12.")
    assert evidence["baseline"]["messages"] == 1
    for candidate in evidence["candidates"]:
        source = SPIKE / folders[candidate["framework"]] / "runner.py"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == candidate["source_sha256"]
        assert candidate["task_success"] is True
        assert candidate["messages"] <= candidate["message_limit"]
        assert candidate["forbidden_tool_denied"] is True
        assert candidate["state_exported"] is True
