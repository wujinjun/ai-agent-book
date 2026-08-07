from pathlib import Path

from rag_spike_llamaindex.main import run


def test_llamaindex_candidate_matches_golden_and_acl() -> None:
    evidence = run(Path(__file__).parents[2] / "spec.json")

    assert evidence["version"] == "0.14.23"
    assert evidence["passed"] is True
    assert [item["top"] for item in evidence["results"]] == ["D1", "D2", None]
