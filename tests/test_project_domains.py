from pathlib import Path

import pytest

from ai_agent_book.project_domains import (
    AssistantSession,
    CodeReviewer,
    Document,
    EnterprisePlatform,
    KnowledgeIndex,
    LocalToolService,
    MultiAgentTeam,
    OfficeAgent,
    ResearchWorkflow,
    StockResearchService,
    WeatherService,
)


def test_assistant_keeps_history_and_streams_usage() -> None:
    session = AssistantSession()
    events = list(session.reply("你好，Agent"))
    assert [event.type for event in events][-1] == "usage"
    assert session.history[-1].role == "assistant"
    assert events[-1].tokens > 0


@pytest.mark.asyncio
async def test_weather_validates_city_and_retries_transient_failure() -> None:
    service = WeatherService(failures_before_success=1)
    result = await service.get_weather("上海")
    assert result.city == "上海"
    assert result.attempts == 2
    with pytest.raises(ValueError):
        await service.get_weather("  ")


def test_local_tools_enforce_root_and_use_parameterized_catalog(tmp_path: Path) -> None:
    (tmp_path / "allowed.txt").write_text("safe", encoding="utf-8")
    tools = LocalToolService(tmp_path)
    assert tools.read_file("allowed.txt") == "safe"
    with pytest.raises(PermissionError):
        tools.read_file("../secret.txt")
    assert tools.query_catalog("Agent")[0]["title"] == "Agent Runtime"


def test_knowledge_index_returns_grounded_citations() -> None:
    index = KnowledgeIndex()
    index.add(
        Document(
            document_id="ch09",
            text="Agent Runtime 管理状态、模型调用与工具循环。",
            source="教材",
            page=9,
        )
    )
    index.add(
        Document(
            document_id="ch13",
            text="RAG 通过检索为生成提供外部证据。",
            source="教材",
            page=13,
        )
    )
    answer = index.answer("什么组件管理工具循环？")
    assert "Agent Runtime" in answer.text
    assert answer.citations[0].document_id == "ch09"


def test_code_reviewer_reports_added_secret_and_broad_exception() -> None:
    diff = "+API_KEY = 'sk-test-secret'\n+try:\n+    run()\n+except Exception:\n+    pass"
    findings = CodeReviewer().review(diff)
    assert {finding.rule for finding in findings} == {"hardcoded-secret", "broad-exception"}


def test_office_agent_cannot_send_without_matching_approval() -> None:
    agent = OfficeAgent()
    draft = agent.create_daily_report(["构建通过", "完成评审"])
    with pytest.raises(PermissionError):
        agent.send(draft, approval_token=None)
    token = agent.approve(draft)
    receipt = agent.send(draft, approval_token=token)
    assert receipt.status == "sent"
    assert len(agent.audit_log) == 3


def test_stock_report_separates_facts_inferences_and_disclaimer() -> None:
    report = StockResearchService().build("DEMO", [100, 102, 101, 105, 104])
    assert report.facts
    assert report.inferences
    assert report.sma_5 == pytest.approx(102.4)
    assert "不构成投资建议" in report.disclaimer


def test_research_workflow_resumes_from_checkpoint_and_reviews() -> None:
    workflow = ResearchWorkflow()
    state = workflow.run("Agent 如何恢复长任务？", stop_after="read")
    assert state.status == "paused"
    resumed = workflow.resume(state.run_id)
    assert resumed.status == "completed"
    assert resumed.reviewed is True


def test_multi_agent_team_has_shared_state_and_hard_termination() -> None:
    result = MultiAgentTeam(max_messages=5).run("增加健康检查")
    assert result.termination == "tests_passed_and_reviewed"
    assert result.message_count <= 5
    assert result.shared_state["tests"] == "passed"


def test_enterprise_platform_is_tenant_isolated_and_traceable() -> None:
    platform = EnterprisePlatform()
    run_a = platform.submit("tenant-a", "user-1", "总结文档")
    run_b = platform.submit("tenant-b", "user-1", "总结文档")
    assert run_a.trace_id != run_b.trace_id
    assert platform.list_runs("tenant-a") == [run_a]
    with pytest.raises(PermissionError):
        platform.get_run("tenant-b", run_a.run_id)
