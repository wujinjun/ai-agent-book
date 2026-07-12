from ai_agent_book.apps.multi_agent_team import DevelopmentTeam


def test_five_role_team_uses_versioned_shared_state_and_terminates() -> None:
    result = DevelopmentTeam(max_messages=5, token_budget=2_000).run("增加健康检查")
    assert result.status == "completed"
    assert result.termination == "tests_passed_and_reviewed"
    assert [message.role for message in result.messages] == [
        "product",
        "planner",
        "coder",
        "tester",
        "reviewer",
    ]
    assert result.shared_state.version == 5
    assert result.shared_state.tests_passed is True
    assert result.estimated_tokens <= 2_000


def test_team_stops_on_budget_instead_of_starting_unbounded_dialogue() -> None:
    result = DevelopmentTeam(max_messages=20, token_budget=10).run("增加复杂功能")
    assert result.status == "stopped"
    assert result.termination == "token_budget_exceeded"
    assert len(result.messages) < 5
