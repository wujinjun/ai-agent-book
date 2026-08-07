import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPIKE = ROOT / "examples/framework_comparison/rag_spike"


def test_rag_framework_spike_pins_candidates_and_shared_fixture() -> None:
    spec = json.loads((SPIKE / "spec.json").read_text(encoding="utf-8"))
    assert [item["expected"] for item in spec["queries"]] == ["D1", "D2", None]
    assert {item["tenant"] for item in spec["documents"]} == {"alpha", "beta"}

    langchain = (SPIKE / "langchain/pyproject.toml").read_text(encoding="utf-8")
    llamaindex = (SPIKE / "llamaindex/pyproject.toml").read_text(encoding="utf-8")
    assert '"langchain==1.3.14"' in langchain
    assert '"llama-index-core==0.14.23"' in llamaindex


def test_committed_rag_evidence_matches_current_sources() -> None:
    evidence = json.loads((SPIKE / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["passed"] is True
    assert {item["candidate"] for item in evidence["candidates"]} == {
        "langchain",
        "llamaindex",
    }
    assert all(item["passed"] for item in evidence["candidates"])
    assert (
        evidence["fixture_sha256"] == hashlib.sha256((SPIKE / "spec.json").read_bytes()).hexdigest()
    )
    assert evidence["candidate_source_sha256"] == {
        "langchain": hashlib.sha256(
            (SPIKE / "langchain/src/rag_spike_langchain/main.py").read_bytes()
        ).hexdigest(),
        "llamaindex": hashlib.sha256(
            (SPIKE / "llamaindex/src/rag_spike_llamaindex/main.py").read_bytes()
        ).hexdigest(),
    }
