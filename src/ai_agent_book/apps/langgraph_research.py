"""项目 8：基于 LangGraph 1.2.9 的可恢复研究工作流。"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, Protocol, TypedDict
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, interrupt
from pydantic import BaseModel, Field

from ai_agent_book.project_service import PrincipalDep


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


class EvidenceItem(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=2_000)
    content: str = Field(min_length=1, max_length=100_000)

    def as_typed_dict(self) -> Evidence:
        return {"title": self.title, "url": self.url, "content": self.content}


class SourcePolicy(BaseModel):
    allowed_domains: frozenset[str]

    def validate_evidence(self, evidence: list[EvidenceItem]) -> None:
        if len({item.url for item in evidence}) < 2:
            raise ValueError("at least two distinct sources are required")
        for item in evidence:
            parsed = urlparse(item.url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise ValueError("evidence URL must use HTTPS")
            if parsed.hostname not in self.allowed_domains:
                raise PermissionError(f"source domain is not allowlisted: {parsed.hostname}")


class DurableResearchRun(BaseModel):
    run_id: str
    tenant_id: str
    topic: str
    status: Literal[
        "queued", "running", "awaiting_approval", "completed", "cancelled", "failed"
    ]
    evidence_hash: str
    attempts: int = Field(ge=0)
    report: str = ""
    error_type: str | None = None


class DurableResearchService:
    """Persisted run journal around LangGraph using deterministic replay.

    The installed LangGraph slice ships only ``InMemorySaver``. This service does
    not mislabel it as durable: it stores immutable inputs and their digest in
    SQLite, rebuilds the graph after restart, replays read-only evidence to the
    interrupt, and then applies the approval command.
    """

    def __init__(
        self,
        database_path: Path,
        *,
        source_policy: SourcePolicy,
        max_review_rounds: int = 2,
    ) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.source_policy = source_policy
        self.max_review_rounds = max_review_rounds
        self._migrate()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat(timespec="milliseconds")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _migrate(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    evidence_hash TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    report TEXT NOT NULL DEFAULT '',
                    error_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_research_queue
                    ON research_runs(tenant_id,status,created_at);
                CREATE TABLE IF NOT EXISTS research_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _canonical_evidence(evidence: list[EvidenceItem]) -> str:
        return json.dumps(
            [item.model_dump() for item in evidence],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _record(row: sqlite3.Row) -> DurableResearchRun:
        return DurableResearchRun(
            run_id=row["run_id"],
            tenant_id=row["tenant_id"],
            topic=row["topic"],
            status=row["status"],
            evidence_hash=row["evidence_hash"],
            attempts=row["attempts"],
            report=row["report"],
            error_type=row["error_type"],
        )

    def submit(
        self,
        topic: str,
        evidence: list[EvidenceItem],
        *,
        tenant_id: str,
    ) -> DurableResearchRun:
        self.source_policy.validate_evidence(evidence)
        canonical = self._canonical_evidence(evidence)
        evidence_hash = sha256(canonical.encode()).hexdigest()
        run_id = str(uuid4())
        now = self._now()
        with self._connect() as db:
            db.execute(
                """INSERT INTO research_runs
                   (run_id,tenant_id,topic,status,evidence_json,evidence_hash,created_at,updated_at)
                   VALUES (?,?,?,'queued',?,?,?,?)""",
                (run_id, tenant_id, topic, canonical, evidence_hash, now, now),
            )
            self._event(db, run_id, "queued")
            row = db.execute("SELECT * FROM research_runs WHERE run_id=?", (run_id,)).fetchone()
            assert row is not None
            return self._record(row)

    @staticmethod
    def _event(db: sqlite3.Connection, run_id: str, event_type: str) -> None:
        db.execute(
            "INSERT INTO research_events(run_id,event_type,created_at) VALUES (?,?,?)",
            (run_id, event_type, DurableResearchService._now()),
        )

    def get(self, tenant_id: str, run_id: str) -> DurableResearchRun:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM research_runs WHERE tenant_id=? AND run_id=?",
                (tenant_id, run_id),
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._record(row)

    def recover_incomplete(self) -> int:
        with self._connect() as db:
            rows = db.execute(
                "SELECT run_id FROM research_runs WHERE status='running'"
            ).fetchall()
            db.execute(
                "UPDATE research_runs SET status='queued',updated_at=? WHERE status='running'",
                (self._now(),),
            )
            for row in rows:
                self._event(db, row["run_id"], "recovered")
        return len(rows)

    def process_next(self, *, tenant_id: str) -> DurableResearchRun | None:
        with self._connect() as db:
            row = db.execute(
                """SELECT * FROM research_runs
                   WHERE tenant_id=? AND status='queued' ORDER BY created_at LIMIT 1""",
                (tenant_id,),
            ).fetchone()
            if row is None:
                return None
            run_id = str(row["run_id"])
            db.execute(
                """UPDATE research_runs SET status='running',attempts=attempts+1,updated_at=?
                   WHERE run_id=? AND status='queued'""",
                (self._now(), run_id),
            )
            self._event(db, run_id, "running")
        try:
            _, paused = self._replay_to_interrupt(run_id)
            status_value = "awaiting_approval" if "__interrupt__" in paused else "failed"
            with self._connect() as db:
                db.execute(
                    "UPDATE research_runs SET status=?,updated_at=? WHERE run_id=?",
                    (status_value, self._now(), run_id),
                )
                self._event(db, run_id, status_value)
                completed = db.execute(
                    "SELECT * FROM research_runs WHERE run_id=?", (run_id,)
                ).fetchone()
                assert completed is not None
                return self._record(completed)
        except Exception as exc:
            return self._fail(run_id, exc)

    def _load_inputs(self, run_id: str) -> tuple[sqlite3.Row, list[EvidenceItem]]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM research_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        canonical = str(row["evidence_json"])
        if sha256(canonical.encode()).hexdigest() != row["evidence_hash"]:
            raise ValueError("persisted evidence digest mismatch")
        evidence = [EvidenceItem.model_validate(item) for item in json.loads(canonical)]
        self.source_policy.validate_evidence(evidence)
        return row, evidence

    def _replay_to_interrupt(self, run_id: str) -> tuple[Any, ResearchState]:
        row, evidence = self._load_inputs(run_id)
        graph = build_research_graph(
            FixtureSearchProvider([item.as_typed_dict() for item in evidence]),
            max_review_rounds=self.max_review_rounds,
        )
        config = {"configurable": {"thread_id": run_id}}
        paused = graph.invoke({"topic": str(row["topic"])}, config)
        return graph, paused

    def approve(
        self,
        tenant_id: str,
        run_id: str,
        *,
        approved: bool,
    ) -> DurableResearchRun:
        current = self.get(tenant_id, run_id)
        if current.status != "awaiting_approval":
            raise ValueError("run is not awaiting approval")
        try:
            graph, paused = self._replay_to_interrupt(run_id)
            if "__interrupt__" not in paused:
                raise ValueError("replay did not reach approval interrupt")
            config = {"configurable": {"thread_id": run_id}}
            result = graph.invoke(Command(resume={"approved": approved}), config)
            target = "completed" if result.get("status") == "completed" else "cancelled"
            report = str(result.get("report", ""))
            with self._connect() as db:
                db.execute(
                    """UPDATE research_runs SET status=?,report=?,updated_at=?
                       WHERE run_id=? AND tenant_id=?""",
                    (target, report, self._now(), run_id, tenant_id),
                )
                self._event(db, run_id, target)
                row = db.execute(
                    "SELECT * FROM research_runs WHERE run_id=?", (run_id,)
                ).fetchone()
                assert row is not None
                return self._record(row)
        except Exception as exc:
            return self._fail(run_id, exc)

    def _fail(self, run_id: str, exc: Exception) -> DurableResearchRun:
        with self._connect() as db:
            db.execute(
                """UPDATE research_runs SET status='failed',error_type=?,updated_at=?
                   WHERE run_id=?""",
                (type(exc).__name__, self._now(), run_id),
            )
            self._event(db, run_id, "failed")
            row = db.execute("SELECT * FROM research_runs WHERE run_id=?", (run_id,)).fetchone()
            assert row is not None
            return self._record(row)


class ResearchCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=10_000)
    evidence: list[EvidenceItem] = Field(min_length=2, max_length=100)


class ApprovalCreate(BaseModel):
    approved: bool


def attach_durable_research_routes(app: FastAPI, service: DurableResearchService) -> None:
    @app.post("/v1/research/runs", response_model=DurableResearchRun)
    async def create_run(body: ResearchCreate, principal: PrincipalDep) -> DurableResearchRun:
        principal.require("project:run")
        try:
            return service.submit(body.topic, body.evidence, tenant_id=principal.tenant_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/v1/research/worker/process-one", response_model=DurableResearchRun | None)
    async def process_one(principal: PrincipalDep) -> DurableResearchRun | None:
        principal.require("project:admin")
        return service.process_next(tenant_id=principal.tenant_id)

    @app.get("/v1/research/runs/{run_id}", response_model=DurableResearchRun)
    async def get_run(run_id: str, principal: PrincipalDep) -> DurableResearchRun:
        try:
            return service.get(principal.tenant_id, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="research run not found") from exc

    @app.post("/v1/research/runs/{run_id}/approval", response_model=DurableResearchRun)
    async def approve_run(
        run_id: str, body: ApprovalCreate, principal: PrincipalDep
    ) -> DurableResearchRun:
        principal.require("project:approve")
        try:
            return service.approve(
                principal.tenant_id, run_id, approved=body.approved
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="research run not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
