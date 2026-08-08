from copy import deepcopy

from scripts.audit_final_acceptance import load_matrix, validate_matrix


def test_current_p9_matrix_is_structurally_valid_and_honest() -> None:
    matrix = load_matrix()
    assert validate_matrix(matrix) == []
    assert matrix["status"] == "complete_repository_scope"
    assert matrix["open_gaps"] == []
    assert len(matrix["excluded_external_gates"]) == 7


def test_complete_status_rejects_open_gaps_and_below_target_scores() -> None:
    matrix = deepcopy(load_matrix())
    matrix["status"] = "complete"
    matrix["open_gaps"] = [{"id": "still-open"}]
    issues = validate_matrix(matrix)
    assert "complete status cannot contain open gaps" in issues
    assert any("score below target" in issue for issue in issues)
    assert any("external evidence" in issue for issue in issues)


def test_repository_scope_completion_cannot_masquerade_as_external_pass() -> None:
    matrix = deepcopy(load_matrix())
    matrix["excluded_external_gates"][0]["status"] = "passed"
    issues = validate_matrix(matrix)

    assert any("must be excluded_not_passed" in issue for issue in issues)


def test_every_gap_has_accountability_and_review_date() -> None:
    matrix = load_matrix()
    for gap in matrix["open_gaps"]:
        assert gap["owner"]
        assert gap["reason"]
        assert gap["next_review"]
