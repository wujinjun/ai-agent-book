from runner import run


def test_approved_path_is_bounded_and_denies_secret() -> None:
    evidence = run()
    assert evidence["task_success"] is True
    assert evidence["messages"] <= evidence["message_limit"]
    assert evidence["forbidden_tool_denied"] is True
    assert evidence["state_exported"] is True


def test_non_approving_reviewer_terminates_at_budget_boundary() -> None:
    evidence = run(force_loop=True)
    assert evidence["task_success"] is False
    assert evidence["termination_reason"] == "budget_exhausted"
    assert evidence["messages"] <= evidence["message_limit"]
