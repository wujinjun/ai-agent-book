from pathlib import Path

from rag_spike_langchain.main import run


def test_langchain_candidate_matches_golden_and_acl() -> None:
    evidence = run(Path(__file__).parents[2] / "spec.json")

    assert evidence["version"] == "1.3.14"
    assert evidence["passed"] is True
    assert [item["top"] for item in evidence["results"]] == ["D1", "D2", None]
