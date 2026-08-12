from ai_agent_book.apps.multi_agent_team import (
    DevelopmentTeam,
    RoleOutput,
    SharedState,
)


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


def test_team_reports_cost_against_single_agent_baseline() -> None:
    comparison = DevelopmentTeam().compare_with_baseline("增加健康检查")

    assert comparison.team.status == comparison.baseline.status == "completed"
    assert len(comparison.baseline.messages) == 1
    assert comparison.extra_messages == 4
    assert comparison.extra_estimated_tokens > 0


class NoProgressRole:
    name = "planner"

    def act(self, state: SharedState) -> RoleOutput:
        return RoleOutput(content="重复相同状态", updates={})


def test_team_stops_when_state_fingerprint_repeats() -> None:
    team = DevelopmentTeam(max_messages=5)
    team.roles = [NoProgressRole(), NoProgressRole()]

    result = team.run("无法推进的任务")

    assert result.status == "stopped"
    assert result.termination == "no_progress_loop_detected"
