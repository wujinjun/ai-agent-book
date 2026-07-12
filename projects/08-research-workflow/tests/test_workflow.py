from ai_agent_book.apps.langgraph_research import FixtureSearchProvider, build_research_graph


def test_insufficient_evidence_terminates() -> None:
    graph = build_research_graph(FixtureSearchProvider([]), max_review_rounds=1)
    result = graph.invoke(
        {"topic": "topic"}, {"configurable": {"thread_id": "project-smoke"}}
    )
    assert result["status"] == "failed"
