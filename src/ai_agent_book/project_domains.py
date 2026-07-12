"""十个教材项目可离线运行的领域实现。

这些实现刻意把外部模型、邮件、行情和工作流 SDK 留在适配器边界之外，
使读者无需账号即可运行测试，同时能看到权限、恢复、引用与终止等工程约束。
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class StreamEvent(BaseModel):
    type: Literal["delta", "usage"]
    text: str = ""
    tokens: int = 0


class AssistantSession:
    """项目 1：带历史、流式事件和确定性 Token 估算的离线会话。"""

    def __init__(self) -> None:
        self.history: list[Message] = []

    def reply(self, prompt: str):  # type: ignore[no-untyped-def]
        if not prompt.strip():
            raise ValueError("prompt 不能为空")
        self.history.append(Message(role="user", content=prompt))
        answer = f"离线助手：已收到“{prompt}”"
        for chunk in re.findall(r".{1,8}", answer):
            yield StreamEvent(type="delta", text=chunk)
        self.history.append(Message(role="assistant", content=answer))
        yield StreamEvent(type="usage", tokens=max(1, (len(prompt) + len(answer)) // 2))


class WeatherResult(BaseModel):
    city: str
    condition: str
    temperature_c: float
    attempts: int = Field(ge=1)
    source: str


class WeatherService:
    """项目 2：展示校验、有限重试和超时边界的天气工具。"""

    def __init__(self, failures_before_success: int = 0, max_attempts: int = 3) -> None:
        self.failures_before_success = failures_before_success
        self.max_attempts = max_attempts

    async def get_weather(self, city: str) -> WeatherResult:
        city = city.strip()
        if not city:
            raise ValueError("city 不能为空")
        for attempt in range(1, self.max_attempts + 1):
            try:
                async with asyncio.timeout(1):
                    await asyncio.sleep(0)
                    if attempt <= self.failures_before_success:
                        raise TimeoutError("模拟瞬时故障")
                    return WeatherResult(
                        city=city,
                        condition="晴",
                        temperature_c=26,
                        attempts=attempt,
                        source="offline-fixture",
                    )
            except TimeoutError:
                if attempt == self.max_attempts:
                    raise
        raise RuntimeError("unreachable")


class LocalToolService:
    """项目 3：受根目录约束的文件工具与参数化 SQLite 查询。"""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE catalog(title TEXT NOT NULL, kind TEXT NOT NULL)")
        self.db.executemany(
            "INSERT INTO catalog VALUES (?, ?)",
            [("Agent Runtime", "chapter"), ("RAG Pipeline", "chapter")],
        )

    def read_file(self, relative_path: str) -> str:
        target = (self.root / relative_path).resolve()
        if not target.is_relative_to(self.root):
            raise PermissionError("路径越过允许根目录")
        return target.read_text(encoding="utf-8")

    def query_catalog(self, keyword: str) -> list[dict[str, str]]:
        rows = self.db.execute(
            "SELECT title, kind FROM catalog WHERE title LIKE ? ORDER BY title", (f"%{keyword}%",)
        ).fetchall()
        return [{"title": str(row[0]), "kind": str(row[1])} for row in rows]


class Document(BaseModel):
    document_id: str
    text: str
    source: str
    page: int = Field(ge=1)


class Citation(BaseModel):
    document_id: str
    source: str
    page: int
    score: float


class GroundedAnswer(BaseModel):
    text: str
    citations: list[Citation]


class KnowledgeIndex:
    """项目 4：可解释的本地词项检索替身，保留来源与页码。"""

    def __init__(self) -> None:
        self.documents: list[Document] = []

    def add(self, document: Document) -> None:
        self.documents.append(document)

    @staticmethod
    def _terms(text: str) -> set[str]:
        latin = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower())
        han = [char for char in text if "\u4e00" <= char <= "\u9fff"]
        return set(latin + han)

    def answer(self, query: str) -> GroundedAnswer:
        query_terms = self._terms(query)
        ranked = sorted(
            self.documents,
            key=lambda doc: len(query_terms & self._terms(doc.text)),
            reverse=True,
        )
        if not ranked or not (query_terms & self._terms(ranked[0].text)):
            return GroundedAnswer(text="证据不足，无法回答。", citations=[])
        top = ranked[0]
        score = len(query_terms & self._terms(top.text)) / max(1, len(query_terms))
        return GroundedAnswer(
            text=f"根据资料：{top.text}",
            citations=[
                Citation(
                    document_id=top.document_id,
                    source=top.source,
                    page=top.page,
                    score=score,
                )
            ],
        )


class Finding(BaseModel):
    rule: str
    risk: Literal["medium", "high"]
    line: int
    message: str


class CodeReviewer:
    """项目 5：只审查新增行的确定性安全规则。"""

    def review(self, diff: str) -> list[Finding]:
        findings: list[Finding] = []
        for line_number, line in enumerate(diff.splitlines(), start=1):
            if line.startswith("+") and re.search(r"(?:API_KEY|SECRET|TOKEN)\s*=\s*['\"]", line):
                findings.append(
                    Finding(
                        rule="hardcoded-secret",
                        risk="high",
                        line=line_number,
                        message="疑似硬编码凭证",
                    )
                )
            if line.startswith("+") and "except Exception" in line:
                findings.append(
                    Finding(
                        rule="broad-exception",
                        risk="medium",
                        line=line_number,
                        message="异常范围过宽",
                    )
                )
        return findings


class Draft(BaseModel):
    draft_id: str
    body: str
    digest: str


class SendReceipt(BaseModel):
    draft_id: str
    status: Literal["sent"]


class OfficeAgent:
    """项目 6：草稿、绑定内容的批准令牌和追加式审计。"""

    def __init__(self) -> None:
        self.audit_log: list[dict[str, str]] = []

    def create_daily_report(self, items: list[str]) -> Draft:
        body = "今日进展：\n" + "\n".join(f"- {item}" for item in items)
        digest = sha256(body.encode()).hexdigest()
        draft = Draft(draft_id=str(uuid4()), body=body, digest=digest)
        self.audit_log.append({"action": "draft_created", "draft_id": draft.draft_id})
        return draft

    def approve(self, draft: Draft) -> str:
        token = sha256(f"approve:{draft.draft_id}:{draft.digest}".encode()).hexdigest()
        self.audit_log.append({"action": "approved", "draft_id": draft.draft_id})
        return token

    def send(self, draft: Draft, approval_token: str | None) -> SendReceipt:
        expected = sha256(f"approve:{draft.draft_id}:{draft.digest}".encode()).hexdigest()
        if approval_token != expected:
            raise PermissionError("发送前需要与当前草稿绑定的人工批准")
        self.audit_log.append({"action": "sent", "draft_id": draft.draft_id})
        return SendReceipt(draft_id=draft.draft_id, status="sent")


class StockReport(BaseModel):
    symbol: str
    as_of: str
    facts: list[str]
    inferences: list[str]
    sma_5: float
    disclaimer: str


class StockResearchService:
    """项目 7：确定性指标与事实/推断分栏，不产生买卖指令。"""

    def build(self, symbol: str, closes: list[float]) -> StockReport:
        if len(closes) < 5 or any(price <= 0 for price in closes):
            raise ValueError("至少需要五个正数收盘价")
        sma = sum(closes[-5:]) / 5
        return StockReport(
            symbol=symbol,
            as_of=datetime.now(UTC).isoformat(timespec="seconds"),
            facts=[f"最近收盘价={closes[-1]:.2f}", f"5 日简单均值={sma:.2f}"],
            inferences=["历史均值仅描述样本，不代表未来方向。"],
            sma_5=sma,
            disclaimer="本报告仅用于教学，不构成投资建议。",
        )


class WorkflowState(BaseModel):
    run_id: str
    topic: str
    step: Literal["plan", "search", "read", "review", "write"]
    status: Literal["paused", "completed"]
    evidence: list[str] = []
    reviewed: bool = False


class ResearchWorkflow:
    """项目 8：以可序列化状态模拟 Checkpoint、恢复和 Reviewer。"""

    steps = ("plan", "search", "read", "review", "write")

    def __init__(self) -> None:
        self.checkpoints: dict[str, WorkflowState] = {}

    def run(self, topic: str, stop_after: str | None = None) -> WorkflowState:
        run_id = str(uuid4())
        state = WorkflowState(run_id=run_id, topic=topic, step="plan", status="paused")
        for step in self.steps:
            state.step = step  # type: ignore[assignment]
            if step == "read":
                state.evidence.append("offline-source: long-running agents need durable state")
            if step == "review":
                state.reviewed = bool(state.evidence)
            self.checkpoints[run_id] = state.model_copy(deep=True)
            if step == stop_after:
                return state
        state.status = "completed"
        self.checkpoints[run_id] = state.model_copy(deep=True)
        return state

    def resume(self, run_id: str) -> WorkflowState:
        saved = self.checkpoints[run_id]
        start = self.steps.index(saved.step) + 1
        state = saved.model_copy(deep=True)
        for step in self.steps[start:]:
            state.step = step  # type: ignore[assignment]
            if step == "review":
                state.reviewed = bool(state.evidence)
            self.checkpoints[run_id] = state.model_copy(deep=True)
        state.status = "completed"
        self.checkpoints[run_id] = state.model_copy(deep=True)
        return state


class TeamResult(BaseModel):
    message_count: int
    termination: str
    shared_state: dict[str, str]


class MultiAgentTeam:
    """项目 9：结构化共享状态和硬消息预算。"""

    def __init__(self, max_messages: int = 5) -> None:
        if max_messages < 4:
            raise ValueError("完整流程至少需要四条结构化消息")
        self.max_messages = max_messages

    def run(self, requirement: str) -> TeamResult:
        state = {
            "requirement": requirement,
            "plan": "实现最小改动并验证",
            "patch": "ready",
            "tests": "passed",
            "review": "approved",
        }
        messages = min(self.max_messages, 5)
        return TeamResult(
            message_count=messages,
            termination="tests_passed_and_reviewed",
            shared_state=state,
        )


class PlatformRun(BaseModel):
    run_id: str
    tenant_id: str
    user_id: str
    prompt: str
    status: Literal["queued"]
    trace_id: str


class EnterprisePlatform:
    """项目 10：内存适配器展示租户隔离、队列状态与 Trace。"""

    def __init__(self) -> None:
        self.runs: dict[str, PlatformRun] = {}

    def submit(self, tenant_id: str, user_id: str, prompt: str) -> PlatformRun:
        run_id = str(uuid4())
        trace_id = sha256(f"{tenant_id}:{run_id}".encode()).hexdigest()[:16]
        run = PlatformRun(
            run_id=run_id,
            tenant_id=tenant_id,
            user_id=user_id,
            prompt=prompt,
            status="queued",
            trace_id=trace_id,
        )
        self.runs[run_id] = run
        return run

    def list_runs(self, tenant_id: str) -> list[PlatformRun]:
        return [run for run in self.runs.values() if run.tenant_id == tenant_id]

    def get_run(self, tenant_id: str, run_id: str) -> PlatformRun:
        run = self.runs[run_id]
        if run.tenant_id != tenant_id:
            raise PermissionError("禁止跨租户访问")
        return run
