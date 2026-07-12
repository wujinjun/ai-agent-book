"""项目 8：基于 LangGraph 1.2.9 的可恢复研究工作流。"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, interrupt


class Evidence(TypedDict):
    title: str
    url: str
    content: str


class ResearchState(TypedDict, total=False):
    topic: str
    plan: list[str]
    evidence: list[Evidence]
    reviewed: bool
    review_rounds: int
    status: Literal["running", "failed", "cancelled", "completed"]
    report: str


class SearchProvider(Protocol):
    def search(self, topic: str) -> list[Evidence]: ...


class FixtureSearchProvider:
    def __init__(self, evidence: list[Evidence], *, failures_before_success: int = 0) -> None:
        self.evidence = evidence
        self.failures_before_success = failures_before_success
        self.calls = 0

    def search(self, topic: str) -> list[Evidence]:
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise RuntimeError("simulated transient search failure")
        return self.evidence


def build_research_graph(
    search_provider: SearchProvider,
    *,
    max_review_rounds: int = 2,
) -> Any:
    """构建并编译真实 LangGraph；返回 CompiledStateGraph。"""

    def plan(state: ResearchState) -> ResearchState:
        return {
            "plan": ["检索多来源", "读取并整理证据", "Reviewer 检查", "人工批准", "生成报告"],
            "evidence": [],
            "reviewed": False,
            "review_rounds": 0,
            "status": "running",
        }

    def search(state: ResearchState) -> ResearchState:
        return {"evidence": search_provider.search(state["topic"])}

    def read(state: ResearchState) -> ResearchState:
        evidence = [item for item in state.get("evidence", []) if item["content"].strip()]
        return {"evidence": evidence}

    def review(state: ResearchState) -> ResearchState:
        evidence = state.get("evidence", [])
        rounds = state.get("review_rounds", 0) + 1
        distinct_sources = {item["url"] for item in evidence}
        return {"reviewed": len(distinct_sources) >= 2, "review_rounds": rounds}

    def route_review(state: ResearchState) -> str:
        if state.get("reviewed"):
            return "approval"
        if state.get("review_rounds", 0) >= max_review_rounds:
            return "fail"
        return "search"

    def approval(state: ResearchState) -> ResearchState:
        decision = interrupt(
            {
                "question": "证据已通过 Reviewer，是否批准生成最终报告？",
                "topic": state["topic"],
                "source_count": len(state.get("evidence", [])),
            }
        )
        approved = isinstance(decision, dict) and bool(decision.get("approved"))
        return {"status": "running" if approved else "cancelled"}

    def route_approval(state: ResearchState) -> str:
        return "write" if state.get("status") == "running" else "fail"

    def write(state: ResearchState) -> ResearchState:
        lines = [f"# 研究报告：{state['topic']}", "", "## 证据"]
        for item in state.get("evidence", []):
            lines.append(f"- [{item['title']}]({item['url']})：{item['content']}")
        lines.extend(["", "## 结论", "结论仅基于上述可核查证据。"])
        return {"report": "\n".join(lines), "status": "completed"}

    def fail(state: ResearchState) -> ResearchState:
        status: Literal["failed", "cancelled"] = (
            "cancelled" if state.get("status") == "cancelled" else "failed"
        )
        return {"status": status}

    builder = StateGraph(ResearchState)
    builder.add_node("plan", plan)
    builder.add_node(
        "search",
        search,
        retry_policy=RetryPolicy(
            initial_interval=0.01,
            max_interval=0.02,
            max_attempts=3,
            jitter=False,
            retry_on=RuntimeError,
        ),
    )
    builder.add_node("read", read)
    builder.add_node("review", review)
    builder.add_node("approval", approval)
    builder.add_node("write", write)
    builder.add_node("fail", fail)
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "search")
    builder.add_edge("search", "read")
    builder.add_edge("read", "review")
    builder.add_conditional_edges(
        "review",
        route_review,
        {"approval": "approval", "search": "search", "fail": "fail"},
    )
    builder.add_conditional_edges(
        "approval",
        route_approval,
        {"write": "write", "fail": "fail"},
    )
    builder.add_edge("write", END)
    builder.add_edge("fail", END)
    return builder.compile(checkpointer=InMemorySaver(), name="research-workflow")
