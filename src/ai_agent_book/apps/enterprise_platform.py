"""项目 10：PostgreSQL/SQLite、Redis、租户权限、RAG、Trace、Eval 与管理 API。"""

from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Protocol, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine, RowMapping

Role = Literal["admin", "member"]


class AgentRecord(BaseModel):
    agent_id: str
    tenant_id: str
    name: str
    kind: str


class ToolRecord(BaseModel):
    tool_id: str
    tenant_id: str
    name: str
    kind: Literal["local", "http", "mcp"]
    endpoint: str


class SessionRecord(BaseModel):
    session_id: str
    tenant_id: str
    user_id: str
    agent_id: str


class RunRecord(BaseModel):
    run_id: str
    tenant_id: str
    session_id: str
    prompt: str
    status: Literal["queued", "running", "succeeded", "failed"]
    output: str = ""
    trace_id: str


class TraceRecord(BaseModel):
    trace_id: str
    run_id: str
    event: str
    details: dict[str, str]
    created_at: datetime


class EvaluationRecord(BaseModel):
    evaluation_id: str
    run_id: str
    passed: bool
    score: float = Field(ge=0, le=1)


class RunQueue(Protocol):
    def push(self, run_id: str) -> None: ...

    def pop(self) -> str | None: ...


class InMemoryRunQueue:
    def __init__(self) -> None:
        self.items: deque[str] = deque()

    def push(self, run_id: str) -> None:
        self.items.append(run_id)

    def pop(self) -> str | None:
        return self.items.popleft() if self.items else None


class RedisRunQueue:
    """Redis 只做唤醒/加速；数据库 queued 状态是任务事实源。"""

    def __init__(self, url: str, *, key: str = "agent-platform:runs") -> None:
        self.client: Redis = Redis.from_url(url, decode_responses=True, socket_timeout=3)
        self.key = key

    def push(self, run_id: str) -> None:
        self.client.rpush(self.key, run_id)

    def pop(self) -> str | None:
        value = self.client.lpop(self.key)
        return cast(str | None, value)


metadata = MetaData()
tenants = Table(
    "tenants",
    metadata,
    Column("tenant_id", String(100), primary_key=True),
    Column("name", String(200), nullable=False),
)
users = Table(
    "users",
    metadata,
    Column("tenant_id", String(100), ForeignKey("tenants.tenant_id"), primary_key=True),
    Column("user_id", String(100), primary_key=True),
    Column("role", String(20), nullable=False),
)
agents = Table(
    "agents",
    metadata,
    Column("agent_id", String(36), primary_key=True),
    Column("tenant_id", String(100), ForeignKey("tenants.tenant_id"), nullable=False),
    Column("name", String(200), nullable=False),
    Column("kind", String(50), nullable=False),
)
tools = Table(
    "tools",
    metadata,
    Column("tool_id", String(36), primary_key=True),
    Column("tenant_id", String(100), ForeignKey("tenants.tenant_id"), nullable=False),
    Column("name", String(200), nullable=False),
    Column("kind", String(20), nullable=False),
    Column("endpoint", Text, nullable=False),
)
sessions = Table(
    "sessions",
    metadata,
    Column("session_id", String(36), primary_key=True),
    Column("tenant_id", String(100), nullable=False),
    Column("user_id", String(100), nullable=False),
    Column("agent_id", String(36), ForeignKey("agents.agent_id"), nullable=False),
    ForeignKeyConstraint(["tenant_id", "user_id"], ["users.tenant_id", "users.user_id"]),
)
documents = Table(
    "documents",
    metadata,
    Column("tenant_id", String(100), nullable=False),
    Column("document_id", String(200), nullable=False),
    Column("content", Text, nullable=False),
    UniqueConstraint("tenant_id", "document_id"),
)
runs = Table(
    "runs",
    metadata,
    Column("run_id", String(36), primary_key=True),
    Column("tenant_id", String(100), nullable=False, index=True),
    Column("session_id", String(36), ForeignKey("sessions.session_id"), nullable=False),
    Column("prompt", Text, nullable=False),
    Column("status", String(20), nullable=False, index=True),
    Column("output", Text, nullable=False, default=""),
    Column("trace_id", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
traces = Table(
    "traces",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tenant_id", String(100), nullable=False),
    Column("trace_id", String(32), nullable=False),
    Column("run_id", String(36), nullable=False, index=True),
    Column("event", String(100), nullable=False),
    Column("details", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
evaluations = Table(
    "evaluations",
    metadata,
    Column("evaluation_id", String(36), primary_key=True),
    Column("tenant_id", String(100), nullable=False),
    Column("run_id", String(36), nullable=False),
    Column("passed", Boolean, nullable=False),
    Column("score", Float, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


class EnterprisePlatform:
    def __init__(
        self,
        database: Path | str,
        *,
        queue: RunQueue | None = None,
    ) -> None:
        if isinstance(database, Path):
            database.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{database}"
        else:
            database_url = database
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        self.queue = queue or InMemoryRunQueue()
        metadata.create_all(self.engine)

    def create_tenant(self, tenant_id: str, name: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(insert(tenants).values(tenant_id=tenant_id, name=name))

    def ensure_tenant(self, tenant_id: str, name: str) -> None:
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(tenants.c.tenant_id).where(tenants.c.tenant_id == tenant_id)
            ).scalar_one_or_none()
            if exists is None:
                connection.execute(insert(tenants).values(tenant_id=tenant_id, name=name))

    def create_user(self, tenant_id: str, user_id: str, *, role: Role) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(users).values(tenant_id=tenant_id, user_id=user_id, role=role)
            )

    def ensure_user(self, tenant_id: str, user_id: str, *, role: Role) -> None:
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(users.c.user_id).where(
                    users.c.tenant_id == tenant_id, users.c.user_id == user_id
                )
            ).scalar_one_or_none()
            if exists is None:
                connection.execute(
                    insert(users).values(tenant_id=tenant_id, user_id=user_id, role=role)
                )

    def _role(self, tenant_id: str, user_id: str) -> str:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(users.c.role).where(
                    users.c.tenant_id == tenant_id, users.c.user_id == user_id
                )
            ).first()
        if row is None:
            raise PermissionError("unknown tenant user")
        return str(row[0])

    def _require_admin(self, tenant_id: str, user_id: str) -> None:
        if self._role(tenant_id, user_id) != "admin":
            raise PermissionError("admin permission required")

    def register_agent(
        self, tenant_id: str, user_id: str, name: str, kind: str
    ) -> AgentRecord:
        self._require_admin(tenant_id, user_id)
        record = AgentRecord(agent_id=str(uuid4()), tenant_id=tenant_id, name=name, kind=kind)
        with self.engine.begin() as connection:
            connection.execute(insert(agents).values(**record.model_dump()))
        return record

    def register_tool(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        *,
        kind: Literal["local", "http", "mcp"],
        endpoint: str,
    ) -> ToolRecord:
        self._require_admin(tenant_id, user_id)
        record = ToolRecord(
            tool_id=str(uuid4()), tenant_id=tenant_id, name=name, kind=kind, endpoint=endpoint
        )
        with self.engine.begin() as connection:
            connection.execute(insert(tools).values(**record.model_dump()))
        return record

    def create_session(self, tenant_id: str, user_id: str, agent_id: str) -> SessionRecord:
        self._role(tenant_id, user_id)
        with self.engine.begin() as connection:
            owner = connection.execute(
                select(agents.c.tenant_id).where(agents.c.agent_id == agent_id)
            ).scalar_one_or_none()
            if owner != tenant_id:
                raise PermissionError("agent does not belong to tenant")
            record = SessionRecord(
                session_id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                agent_id=agent_id,
            )
            connection.execute(insert(sessions).values(**record.model_dump()))
        return record

    def add_document(self, tenant_id: str, document_id: str, content: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                delete(documents).where(
                    documents.c.tenant_id == tenant_id,
                    documents.c.document_id == document_id,
                )
            )
            connection.execute(
                insert(documents).values(
                    tenant_id=tenant_id, document_id=document_id, content=content
                )
            )

    def submit_run(
        self, tenant_id: str, user_id: str, session_id: str, prompt: str
    ) -> RunRecord:
        self._role(tenant_id, user_id)
        with self.engine.begin() as connection:
            session = connection.execute(
                select(sessions.c.tenant_id, sessions.c.user_id).where(
                    sessions.c.session_id == session_id
                )
            ).mappings().first()
            if (
                session is None
                or session["tenant_id"] != tenant_id
                or session["user_id"] != user_id
            ):
                raise PermissionError("session access denied")
            record = RunRecord(
                run_id=str(uuid4()),
                tenant_id=tenant_id,
                session_id=session_id,
                prompt=prompt,
                status="queued",
                trace_id=uuid4().hex,
            )
            connection.execute(
                insert(runs).values(**record.model_dump(), created_at=datetime.now(UTC))
            )
            self._trace(connection, record, "run.queued", {"user_id": user_id})
        try:
            self.queue.push(record.run_id)
        except Exception:
            # Queue 是唤醒机制；数据库扫描保证任务不会因 Redis 短暂失败而丢失。
            pass
        return record

    def process_next(self) -> RunRecord | None:
        hinted_id: str | None
        try:
            hinted_id = self.queue.pop()
        except Exception:
            hinted_id = None
        with self.engine.begin() as connection:
            query = (
                select(runs)
                .where(runs.c.status == "queued")
                .order_by(runs.c.created_at)
                .limit(1)
            )
            if hinted_id:
                query = select(runs).where(
                    runs.c.run_id == hinted_id, runs.c.status == "queued"
                ).limit(1)
            row = connection.execute(query.with_for_update(skip_locked=True)).mappings().first()
            if row is None and hinted_id:
                row = connection.execute(
                    select(runs)
                    .where(runs.c.status == "queued")
                    .order_by(runs.c.created_at)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                ).mappings().first()
            if row is None:
                return None
            running = self._mapping_to_run(row, status="running")
            connection.execute(
                update(runs).where(runs.c.run_id == running.run_id).values(status="running")
            )
            self._trace(connection, running, "run.started", {})
            docs = connection.execute(
                select(documents.c.document_id, documents.c.content).where(
                    documents.c.tenant_id == running.tenant_id
                )
            ).mappings().all()
            terms = {char for char in running.prompt if "\u4e00" <= char <= "\u9fff"}
            ranked = sorted(
                docs,
                key=lambda item: len(terms & set(str(item["content"]))),
                reverse=True,
            )
            evidence = str(ranked[0]["content"]) if ranked and terms else ""
            output = (
                f"根据租户知识库：{evidence} [来源：{ranked[0]['document_id']}]"
                if evidence
                else f"Assistant 已处理：{running.prompt}"
            )
            connection.execute(
                update(runs)
                .where(runs.c.run_id == running.run_id)
                .values(status="succeeded", output=output)
            )
            completed = running.model_copy(update={"status": "succeeded", "output": output})
            self._trace(connection, completed, "run.succeeded", {"rag": str(bool(evidence))})
            return completed

    def get_run(self, tenant_id: str, run_id: str) -> RunRecord:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(runs).where(runs.c.run_id == run_id)
            ).mappings().first()
        if row is None or row["tenant_id"] != tenant_id:
            raise PermissionError("run access denied")
        return self._mapping_to_run(row)

    def list_runs(self, tenant_id: str, user_id: str) -> list[RunRecord]:
        self._require_admin(tenant_id, user_id)
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(runs).where(runs.c.tenant_id == tenant_id).order_by(runs.c.created_at.desc())
            ).mappings().all()
        return [self._mapping_to_run(row) for row in rows]

    def list_traces(self, tenant_id: str, run_id: str) -> list[TraceRecord]:
        self.get_run(tenant_id, run_id)
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(traces)
                .where(traces.c.tenant_id == tenant_id, traces.c.run_id == run_id)
                .order_by(traces.c.id)
            ).mappings().all()
        return [
            TraceRecord(
                trace_id=str(row["trace_id"]),
                run_id=str(row["run_id"]),
                event=str(row["event"]),
                details=json.loads(str(row["details"])),
                created_at=cast(datetime, row["created_at"]),
            )
            for row in rows
        ]

    def evaluate_run(
        self, tenant_id: str, user_id: str, run_id: str
    ) -> EvaluationRecord:
        self._require_admin(tenant_id, user_id)
        run = self.get_run(tenant_id, run_id)
        passed = run.status == "succeeded" and bool(run.output)
        record = EvaluationRecord(
            evaluation_id=str(uuid4()), run_id=run_id, passed=passed, score=1.0 if passed else 0.0
        )
        with self.engine.begin() as connection:
            connection.execute(
                insert(evaluations).values(
                    **record.model_dump(), tenant_id=tenant_id, created_at=datetime.now(UTC)
                )
            )
        return record

    @staticmethod
    def _mapping_to_run(row: RowMapping, *, status: str | None = None) -> RunRecord:
        return RunRecord(
            run_id=str(row["run_id"]),
            tenant_id=str(row["tenant_id"]),
            session_id=str(row["session_id"]),
            prompt=str(row["prompt"]),
            status=status or str(row["status"]),  # type: ignore[arg-type]
            output=str(row["output"]),
            trace_id=str(row["trace_id"]),
        )

    @staticmethod
    def _trace(
        connection: object,
        run: RunRecord,
        event: str,
        details: dict[str, str],
    ) -> None:
        connection.execute(  # type: ignore[attr-defined]
            insert(traces).values(
                tenant_id=run.tenant_id,
                trace_id=run.trace_id,
                run_id=run.run_id,
                event=event,
                details=json.dumps(details, ensure_ascii=False),
                created_at=datetime.now(UTC),
            )
        )


class Principal(BaseModel):
    tenant_id: str
    user_id: str


def principal(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-ID")],
    x_user_id: Annotated[str, Header(alias="X-User-ID")],
) -> Principal:
    return Principal(tenant_id=x_tenant_id, user_id=x_user_id)


class AgentCreate(BaseModel):
    name: str
    kind: str


class ToolCreate(BaseModel):
    name: str
    kind: Literal["local", "http", "mcp"]
    endpoint: str


class SessionCreate(BaseModel):
    agent_id: str


class RunCreate(BaseModel):
    session_id: str
    prompt: str = Field(min_length=1, max_length=20_000)


def create_enterprise_app(platform: EnterprisePlatform) -> FastAPI:
    app = FastAPI(title="Enterprise Agent Platform", version="1.0.0")

    def forbidden(exc: PermissionError) -> HTTPException:
        return HTTPException(status_code=403, detail=str(exc))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/admin/runs", response_model=list[RunRecord])
    async def admin_runs(identity: Annotated[Principal, Depends(principal)]) -> list[RunRecord]:
        try:
            return platform.list_runs(identity.tenant_id, identity.user_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/admin/agents", response_model=AgentRecord)
    async def create_agent(
        body: AgentCreate, identity: Annotated[Principal, Depends(principal)]
    ) -> AgentRecord:
        try:
            return platform.register_agent(
                identity.tenant_id, identity.user_id, body.name, body.kind
            )
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/admin/tools", response_model=ToolRecord)
    async def create_tool(
        body: ToolCreate, identity: Annotated[Principal, Depends(principal)]
    ) -> ToolRecord:
        try:
            return platform.register_tool(
                identity.tenant_id,
                identity.user_id,
                body.name,
                kind=body.kind,
                endpoint=body.endpoint,
            )
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/sessions", response_model=SessionRecord)
    async def create_session(
        body: SessionCreate, identity: Annotated[Principal, Depends(principal)]
    ) -> SessionRecord:
        try:
            return platform.create_session(identity.tenant_id, identity.user_id, body.agent_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/runs", response_model=RunRecord)
    async def create_run(
        body: RunCreate, identity: Annotated[Principal, Depends(principal)]
    ) -> RunRecord:
        try:
            return platform.submit_run(
                identity.tenant_id, identity.user_id, body.session_id, body.prompt
            )
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/worker/process-one", response_model=RunRecord | None)
    async def process_one(identity: Annotated[Principal, Depends(principal)]) -> RunRecord | None:
        try:
            platform._require_admin(identity.tenant_id, identity.user_id)
            return platform.process_next()
        except PermissionError as exc:
            raise forbidden(exc) from exc

    return app
