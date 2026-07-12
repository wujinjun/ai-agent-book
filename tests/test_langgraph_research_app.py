from langgraph.types import Command

from ai_agent_book.apps.langgraph_research import FixtureSearchProvider, build_research_graph


def test_real_langgraph_retries_checkpoints_interrupts_and_resumes() -> None:
    search = FixtureSearchProvider(
        [
            {
                "title": "状态恢复",
                "url": "https://example.test/1",
                "content": "Checkpoint 保存状态。",
            },
            {
                "title": "人工审批",
                "url": "https://example.test/2",
                "content": "Interrupt 等待人工输入。",
            },
        ],
        failures_before_success=1,
    )
    graph = build_research_graph(search)
    config = {"configurable": {"thread_id": "research-1"}}

    paused = graph.invoke({"topic": "Agent 如何恢复长任务？"}, config)

    assert paused["reviewed"] is True
    assert "__interrupt__" in paused
    assert search.calls == 2
    snapshot = graph.get_state(config)
    assert snapshot.next == ("approval",)
    assert snapshot.values["evidence"]

    completed = graph.invoke(Command(resume={"approved": True}), config)
    assert completed["status"] == "completed"
    assert "Checkpoint" in completed["report"]


def test_reviewer_rejects_insufficient_evidence_before_approval() -> None:
    search = FixtureSearchProvider(
        [{"title": "单一来源", "url": "https://example.test/1", "content": "只有一条证据。"}]
    )
    graph = build_research_graph(search, max_review_rounds=1)
    config = {"configurable": {"thread_id": "research-insufficient"}}
    result = graph.invoke({"topic": "研究问题"}, config)
    assert result["status"] == "failed"
    assert "__interrupt__" not in result
