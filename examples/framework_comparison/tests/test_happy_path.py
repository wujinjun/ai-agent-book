from framework_comparison.io import load_evidence, load_spec
from framework_comparison.scoring import compare_candidates, render_adr


def test_verified_evidence_completes_the_same_fixture() -> None:
    evidence = load_evidence()
    assert len(evidence) == 3
    assert all(item.task_success for item in evidence)
    assert all(item.tool_accuracy == 1.0 for item in evidence)
    assert all(item.recovered_from_transient for item in evidence)
    assert all(set(item.report.citations) == {"D1", "D2"} for item in evidence)


def test_comparison_produces_reversible_adr() -> None:
    evidence = load_evidence()
    result = compare_candidates(load_spec(), evidence)
    adr = render_adr(result, evidence)
    assert result.selected in {item.candidate for item in evidence}
    assert "## Uncertainty" in adr
    assert "## Rollback" in adr
    assert "Review triggers" in adr
