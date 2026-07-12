"""十个教材项目的离线可运行核心，在线集成通过适配器扩展。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal


@dataclass(frozen=True)
class ProjectDefinition:
    project_id: int
    slug: str
    title: str
    features: tuple[str, ...]


@dataclass(frozen=True)
class ProjectResult:
    project_id: int
    status: Literal["completed", "approval_required"]
    output: str
    data: dict[str, Any]
    trace: tuple[str, ...]


PROJECTS = {
    1: ProjectDefinition(
        1, "minimal-assistant", "最小 AI Assistant", ("history", "tokens", "streaming")
    ),
    2: ProjectDefinition(
        2, "weather-tool-agent", "天气与工具 Agent", ("tools", "validation", "approval")
    ),
    3: ProjectDefinition(3, "mcp-local-agent", "MCP 本地工具 Agent", ("mcp", "files", "database")),
    4: ProjectDefinition(
        4, "knowledge-agent", "企业知识库 Agent", ("rag", "citations", "evaluation")
    ),
    5: ProjectDefinition(5, "code-review-agent", "代码 Review Agent", ("diff", "rules", "risk")),
    6: ProjectDefinition(6, "office-agent", "自动办公 Agent", ("mail", "calendar", "audit")),
    7: ProjectDefinition(
        7, "stock-research-agent", "股票研究 Agent", ("market", "sources", "disclaimer")
    ),
    8: ProjectDefinition(
        8, "research-workflow", "研究工作流 Agent", ("plan", "review", "checkpoint")
    ),
    9: ProjectDefinition(
        9, "multi-agent-dev-team", "Multi-Agent 开发团队", ("roles", "shared-state", "termination")
    ),
    10: ProjectDefinition(
        10, "enterprise-platform", "企业级 Agent 平台", ("tenants", "queue", "tracing")
    ),
}


def _trace(project_id: int, *events: str) -> tuple[str, ...]:
    return (f"project:{project_id}", "mode:offline", *events)


def run_project(project_id: int, prompt: str) -> ProjectResult:
    """运行无需密钥的确定性演示；真实外部服务在各项目适配器中替换。"""
    if project_id not in PROJECTS:
        raise ValueError(f"未知项目: {project_id}")
    if not prompt.strip():
        raise ValueError("prompt 不能为空")

    now = datetime.now(UTC).isoformat(timespec="seconds")
    if project_id == 1:
        tokens = max(1, len(prompt) // 2)
        return ProjectResult(
            1,
            "completed",
            f"离线助手已收到：{prompt}",
            {"estimated_tokens": tokens, "history_size": 1},
            _trace(1, "history_saved", "stream_complete"),
        )
    if project_id == 2:
        return ProjectResult(
            2,
            "completed",
            "Mock 天气：上海，晴，26°C（教学数据）",
            {"tool": "get_weather", "city": "上海", "mock": True},
            _trace(2, "args_validated", "tool_called"),
        )
    if project_id == 3:
        return ProjectResult(
            3,
            "completed",
            "MCP 离线资源读取成功",
            {"tools": ["read_file", "system_info", "query_catalog"], "read_only": True},
            _trace(3, "capabilities_discovered", "resource_read"),
        )
    if project_id == 4:
        return ProjectResult(
            4,
            "completed",
            "知识库回答：Agent Runtime 管理状态与工具循环。[来源：chapter-09]",
            {"citations": [{"document_id": "chapter-09", "score": 1.0}], "faithful": True},
            _trace(4, "retrieved", "reranked", "cited"),
        )
    if project_id == 5:
        return ProjectResult(
            5,
            "completed",
            "Review：发现宽泛异常捕获，风险等级 medium。",
            {"findings": [{"rule": "broad-exception", "risk": "medium", "line": 1}]},
            _trace(5, "diff_parsed", "rules_run", "report_generated"),
        )
    if project_id == 6:
        return ProjectResult(
            6,
            "approval_required",
            "邮件摘要与日报草稿已生成，发送前需要人工批准。",
            {
                "summary": "离线邮件摘要",
                "pending_actions": ["send_daily_report"],
                "audit_time": now,
            },
            _trace(6, "mail_mock_read", "draft_created", "approval_requested"),
        )
    if project_id == 7:
        return ProjectResult(
            7,
            "completed",
            "研究报告使用教学数据，不构成投资建议。事实与模型推断已分栏。",
            {
                "as_of": now,
                "facts": [{"source": "mock-market", "close": 100.0}],
                "inferences": ["样例价格波动不能用于预测未来"],
            },
            _trace(7, "facts_loaded", "indicators_computed", "inference_labeled"),
        )
    if project_id == 8:
        return ProjectResult(
            8,
            "completed",
            "研究流程完成：计划、检索、证据表、Reviewer 与报告均已通过离线演示。",
            {"checkpoint": "reviewed", "steps": ["plan", "search", "read", "review", "write"]},
            _trace(8, "checkpoint_saved", "review_passed"),
        )
    if project_id == 9:
        return ProjectResult(
            9,
            "completed",
            "开发团队完成一个受测变更，并在 Reviewer 通过后终止。",
            {
                "roles": ["product", "planner", "coder", "reviewer", "tester"],
                "messages": 5,
                "termination": "tests_passed_and_reviewed",
            },
            _trace(9, "shared_state_updated", "terminated"),
        )

    tenant = prompt.split(":", 1)[0].strip() if ":" in prompt else "demo-tenant"
    trace_id = sha256(f"{tenant}:{prompt}".encode()).hexdigest()[:16]
    return ProjectResult(
        10,
        "completed",
        "企业平台离线任务已创建并完成。",
        {
            "tenant_id": tenant,
            "trace_id": trace_id,
            "queue_state": "succeeded",
            "permissions": ["agent:run"],
        },
        _trace(10, f"tenant:{tenant}", f"trace:{trace_id}"),
    )
