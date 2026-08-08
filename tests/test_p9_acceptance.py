from copy import deepcopy

from scripts.audit_final_acceptance import load_matrix, validate_matrix


def test_current_p9_matrix_is_structurally_valid_and_honest() -> None:
    matrix = load_matrix()
    assert validate_matrix(matrix) == []
    assert matrix["status"] == "in_progress_external_evidence_required"
    assert matrix["open_gaps"]


def test_complete_status_rejects_open_gaps_and_below_target_scores() -> None:
    matrix = deepcopy(load_matrix())
    matrix["status"] = "complete"
    issues = validate_matrix(matrix)
    assert "complete status cannot contain open gaps" in issues
    assert any("score below target" in issue for issue in issues)
    assert any("external evidence" in issue for issue in issues)


def test_every_gap_has_accountability_and_review_date() -> None:
    matrix = load_matrix()
    for gap in matrix["open_gaps"]:
        assert gap["owner"]
        assert gap["reason"]
        assert gap["next_review"]
