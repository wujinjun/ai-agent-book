from ai_agent_book.apps.multi_agent_team import DevelopmentTeam


def test_team_has_hard_termination() -> None:
    assert DevelopmentTeam().run("change").termination == "tests_passed_and_reviewed"
