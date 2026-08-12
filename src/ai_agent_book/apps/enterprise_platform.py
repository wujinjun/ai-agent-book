"""项目 10：PostgreSQL/SQLite、Redis、租户权限、RAG、Trace、Eval 与管理 API。"""

from __future__ import annotations

import base64
import binascii
import hmac
import inspect as python_inspect
import json
import sqlite3
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal, Protocol, cast
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
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
    inspect,
    or_,
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
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
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


class DeadLetterRecord(BaseModel):
    run_id: str
    tenant_id: str
    error_type: str
    attempts: int = Field(ge=1)
    created_at: datetime


class ReplayApprovalRecord(BaseModel):
    run_id: str
    content_hash: str
    expires_at: datetime


class RunCancelled(RuntimeError):
    """执行器在显式安全检查点观察到取消请求。"""


class RunExecutionContext:
    """长任务执行器使用的协作式控制面；不会异步杀死业务代码。"""

    def __init__(self, platform: EnterprisePlatform, run: RunRecord, worker_id: str) -> None:
        self._platform = platform
        self.run = run
        self.worker_id = worker_id

    def heartbeat(self) -> datetime:
        return self._platform.heartbeat_run(self.run.run_id, self.worker_id)

    def cancellation_requested(self) -> bool:
        return self._platform.is_cancellation_requested(self.run.run_id, self.worker_id)

    def checkpoint(self) -> None:
        if self.cancellation_requested():
            raise RunCancelled(f"run {self.run.run_id} cancellation requested")


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
    Column("worker_id", String(64), nullable=True),
    Column("lease_expires_at", DateTime(timezone=True), nullable=True),
    Column("cancel_requested", Boolean, nullable=False, default=False),
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
schema_versions = Table(
    "schema_versions",
    metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", DateTime(timezone=True), nullable=False),
)
run_failures = Table(
    "run_failures",
    metadata,
    Column("run_id", String(36), primary_key=True),
    Column("attempts", Integer, nullable=False),
    Column("error_type", String(100), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
dead_letters = Table(
    "dead_letters",
    metadata,
    Column("run_id", String(36), primary_key=True),
    Column("tenant_id", String(100), nullable=False, index=True),
    Column("error_type", String(100), nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
replay_approvals = Table(
    "replay_approvals",
    metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("tenant_id", String(100), nullable=False, index=True),
    Column("content_hash", String(64), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True), nullable=True),
)


RunExecutor = Callable[..., str]
ContextRunExecutor = Callable[[RunRecord, list[dict[str, str]], RunExecutionContext], str]


class EnterprisePlatform:
    def __init__(
        self,
        database: Path | str,
        *,
        queue: RunQueue | None = None,
        run_executor: RunExecutor | None = None,
        max_attempts: int = 3,
        lease_seconds: int = 60,
    ) -> None:
        if isinstance(database, Path):
            database.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{database}"
        else:
            database_url = database
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        self.queue = queue or InMemoryRunQueue()
        self.run_executor = run_executor or self._default_execute
        self.max_attempts = max_attempts
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        self.lease_seconds = lease_seconds
        metadata.create_all(self.engine)
        self._migrate_run_leases()
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(schema_versions.c.version).where(schema_versions.c.version == 1)
            ).scalar_one_or_none()
            if exists is None:
                connection.execute(
                    insert(schema_versions).values(version=1, applied_at=datetime.now(UTC))
                )
            version_two = connection.execute(
                select(schema_versions.c.version).where(schema_versions.c.version == 2)
            ).scalar_one_or_none()
            if version_two is None:
                connection.execute(
                    insert(schema_versions).values(version=2, applied_at=datetime.now(UTC))
                )
            version_three = connection.execute(
                select(schema_versions.c.version).where(schema_versions.c.version == 3)
            ).scalar_one_or_none()
            if version_three is None:
                connection.execute(
                    insert(schema_versions).values(version=3, applied_at=datetime.now(UTC))
                )

    def _migrate_run_leases(self) -> None:
        """为已有 v1 数据库增加租约列；生产环境应使用正式迁移工具。"""
        existing = {str(item["name"]) for item in inspect(self.engine).get_columns("runs")}
        statements: list[str] = []
        if "worker_id" not in existing:
            statements.append("ALTER TABLE runs ADD COLUMN worker_id VARCHAR(64)")
        if "lease_expires_at" not in existing:
            statements.append("ALTER TABLE runs ADD COLUMN lease_expires_at TIMESTAMP")
        if "cancel_requested" not in existing:
            statements.append(
                "ALTER TABLE runs ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT 0"
            )
        if statements:
            with self.engine.begin() as connection:
                for statement in statements:
                    connection.exec_driver_sql(statement)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        """SQLite 可能返回 naive datetime；领域层统一按 UTC 解释。"""
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

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

    def process_next(self, *, tenant_id: str | None = None) -> RunRecord | None:
        """领取租户限定 Run，先提交短事务，再在事务外执行 Provider。"""
        hinted_id: str | None
        try:
            hinted_id = self.queue.pop()
        except Exception:
            hinted_id = None
        current = datetime.now(UTC)
        claimable = or_(
            runs.c.status == "queued",
            (runs.c.status == "running") & (runs.c.lease_expires_at < current),
        )
        worker_id = uuid4().hex
        with self.engine.begin() as connection:
            query = select(runs).where(claimable)
            if tenant_id:
                query = query.where(runs.c.tenant_id == tenant_id)
            query = query.order_by(runs.c.created_at).limit(1)
            if hinted_id:
                query = select(runs).where(runs.c.run_id == hinted_id, claimable)
                if tenant_id:
                    query = query.where(runs.c.tenant_id == tenant_id)
                query = query.limit(1)
            row = connection.execute(query.with_for_update(skip_locked=True)).mappings().first()
            if row is None and hinted_id:
                fallback = select(runs).where(claimable)
                if tenant_id:
                    fallback = fallback.where(runs.c.tenant_id == tenant_id)
                fallback = fallback.order_by(runs.c.created_at).limit(1)
                row = connection.execute(
                    fallback.with_for_update(skip_locked=True)
                ).mappings().first()
            if row is None:
                return None
            running = self._mapping_to_run(row, status="running")
            claimed = connection.execute(
                update(runs)
                .where(runs.c.run_id == running.run_id, claimable)
                .values(
                    status="running",
                    worker_id=worker_id,
                    lease_expires_at=current + timedelta(seconds=self.lease_seconds),
                )
            )
            if claimed.rowcount != 1:
                return None
            self._trace(connection, running, "run.started", {})

        with self.engine.connect() as connection:
            document_rows = connection.execute(
                select(documents.c.document_id, documents.c.content).where(
                    documents.c.tenant_id == running.tenant_id
                )
            ).mappings().all()
            docs = [
                {"document_id": str(item["document_id"]), "content": str(item["content"])}
                for item in document_rows
            ]
        try:
            context = RunExecutionContext(self, running, worker_id)
            context.checkpoint()
            parameters = python_inspect.signature(self.run_executor).parameters
            if len(parameters) >= 3:
                context_executor = cast(ContextRunExecutor, self.run_executor)
                output = context_executor(running, docs, context)
            else:
                output = self.run_executor(running, docs)
            context.checkpoint()
        except RunCancelled:
            with self.engine.begin() as connection:
                cancelled_write = connection.execute(
                    update(runs)
                    .where(
                        runs.c.run_id == running.run_id,
                        runs.c.status == "running",
                        runs.c.worker_id == worker_id,
                        runs.c.cancel_requested.is_(True),
                    )
                    .values(
                        status="cancelled",
                        output="cancelled",
                        worker_id=None,
                        lease_expires_at=None,
                    )
                )
                if cancelled_write.rowcount != 1:
                    raise RuntimeError("run lease was lost before cancellation") from None
                cancelled = running.model_copy(
                    update={"status": "cancelled", "output": "cancelled"}
                )
                self._trace(connection, cancelled, "run.cancelled", {"source": "worker"})
                return cancelled
        except Exception as exc:
            with self.engine.begin() as connection:
                return self._record_failure(connection, running, exc, worker_id=worker_id)
        with self.engine.begin() as connection:
            completed_write = connection.execute(
                update(runs)
                .where(
                    runs.c.run_id == running.run_id,
                    runs.c.status == "running",
                    runs.c.worker_id == worker_id,
                )
                .values(
                    status="succeeded",
                    output=output,
                    worker_id=None,
                    lease_expires_at=None,
                )
            )
            if completed_write.rowcount != 1:
                raise RuntimeError("run lease was lost before completion")
            completed = running.model_copy(update={"status": "succeeded", "output": output})
            self._trace(connection, completed, "run.succeeded", {"rag": str(bool(docs))})
            return completed

    def heartbeat_run(self, run_id: str, worker_id: str) -> datetime:
        """仅当前租约持有者可续租；worker_id 同时承担 fencing token 的作用。"""
        expires_at = datetime.now(UTC) + timedelta(seconds=self.lease_seconds)
        with self.engine.begin() as connection:
            renewed = connection.execute(
                update(runs)
                .where(
                    runs.c.run_id == run_id,
                    runs.c.status == "running",
                    runs.c.worker_id == worker_id,
                )
                .values(lease_expires_at=expires_at)
            )
        if renewed.rowcount != 1:
            raise RuntimeError("run lease cannot be renewed by this worker")
        return expires_at

    def is_cancellation_requested(self, run_id: str, worker_id: str) -> bool:
        with self.engine.connect() as connection:
            value = connection.execute(
                select(runs.c.cancel_requested).where(
                    runs.c.run_id == run_id,
                    runs.c.status == "running",
                    runs.c.worker_id == worker_id,
                )
            ).scalar_one_or_none()
        if value is None:
            raise RuntimeError("run lease is no longer owned by this worker")
        return bool(value)

    @staticmethod
    def _default_execute(run: RunRecord, docs: list[dict[str, str]]) -> str:
        terms = {char for char in run.prompt if "\u4e00" <= char <= "\u9fff"}
        ranked = sorted(
            docs,
            key=lambda item: len(terms & set(item["content"])),
            reverse=True,
        )
        evidence = ranked[0]["content"] if ranked and terms else ""
        return (
            f"根据租户知识库：{evidence} [来源：{ranked[0]['document_id']}]"
            if evidence
            else f"Assistant 已处理：{run.prompt}"
        )

    def _record_failure(
        self,
        connection: object,
        run: RunRecord,
        exc: Exception,
        *,
        worker_id: str,
    ) -> RunRecord:
        error_type = type(exc).__name__
        existing = connection.execute(  # type: ignore[attr-defined]
            select(run_failures.c.attempts).where(run_failures.c.run_id == run.run_id)
        ).scalar_one_or_none()
        attempts = int(existing or 0) + 1
        connection.execute(  # type: ignore[attr-defined]
            delete(run_failures).where(run_failures.c.run_id == run.run_id)
        )
        connection.execute(  # type: ignore[attr-defined]
            insert(run_failures).values(
                run_id=run.run_id,
                attempts=attempts,
                error_type=error_type,
                updated_at=datetime.now(UTC),
            )
        )
        if attempts < self.max_attempts:
            status_value: Literal["queued", "failed"] = "queued"
            event = "run.retry_scheduled"
        else:
            status_value = "failed"
            event = "run.dead_lettered"
            connection.execute(  # type: ignore[attr-defined]
                delete(dead_letters).where(dead_letters.c.run_id == run.run_id)
            )
            connection.execute(  # type: ignore[attr-defined]
                insert(dead_letters).values(
                    run_id=run.run_id,
                    tenant_id=run.tenant_id,
                    error_type=error_type,
                    attempts=attempts,
                    created_at=datetime.now(UTC),
                )
            )
        updated = connection.execute(  # type: ignore[attr-defined]
            update(runs)
            .where(
                runs.c.run_id == run.run_id,
                runs.c.status == "running",
                runs.c.worker_id == worker_id,
            )
            .values(
                status=status_value,
                worker_id=None,
                lease_expires_at=None,
            )
        )
        if updated.rowcount != 1:
            raise RuntimeError("run lease was lost before failure recording")
        failed = run.model_copy(update={"status": status_value})
        self._trace(
            connection,
            failed,
            event,
            {"error_type": error_type, "attempts": str(attempts)},
        )
        if status_value == "queued":
            try:
                self.queue.push(run.run_id)
            except Exception:
                pass
        return failed

    def cancel_run(self, tenant_id: str, user_id: str, run_id: str) -> RunRecord:
        role = self._role(tenant_id, user_id)
        current = self.get_run(tenant_id, run_id)
        if role != "admin":
            with self.engine.connect() as connection:
                owner = connection.execute(
                    select(sessions.c.user_id)
                    .select_from(runs.join(sessions, runs.c.session_id == sessions.c.session_id))
                    .where(runs.c.run_id == run_id)
                ).scalar_one_or_none()
            if owner != user_id:
                raise PermissionError("run cancellation denied")
        if current.status not in {"queued", "running"}:
            raise ValueError("only queued or running runs can be cancelled")
        with self.engine.begin() as connection:
            if current.status == "running":
                connection.execute(
                    update(runs)
                    .where(runs.c.run_id == run_id, runs.c.status == "running")
                    .values(cancel_requested=True)
                )
                self._trace(connection, current, "run.cancel_requested", {"user_id": user_id})
                return current
            connection.execute(
                update(runs)
                .where(runs.c.run_id == run_id, runs.c.status == "queued")
                .values(status="cancelled", output="cancelled", cancel_requested=True)
            )
            cancelled = current.model_copy(update={"status": "cancelled", "output": "cancelled"})
            self._trace(connection, cancelled, "run.cancelled", {"user_id": user_id})
            return cancelled

    def list_dead_letters(self, tenant_id: str, user_id: str) -> list[DeadLetterRecord]:
        self._require_admin(tenant_id, user_id)
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(dead_letters)
                .where(dead_letters.c.tenant_id == tenant_id)
                .order_by(dead_letters.c.created_at)
            ).mappings().all()
        return [
            DeadLetterRecord(
                run_id=str(row["run_id"]),
                tenant_id=str(row["tenant_id"]),
                error_type=str(row["error_type"]),
                attempts=int(row["attempts"]),
                created_at=cast(datetime, row["created_at"]),
            )
            for row in rows
        ]

    def _dead_letter_content_hash(self, connection: object, run_id: str) -> str:
        row = connection.execute(  # type: ignore[attr-defined]
            select(
                runs.c.prompt,
                runs.c.trace_id,
                dead_letters.c.error_type,
                dead_letters.c.attempts,
            )
            .select_from(runs.join(dead_letters, runs.c.run_id == dead_letters.c.run_id))
            .where(runs.c.run_id == run_id)
        ).mappings().first()
        if row is None:
            raise KeyError(run_id)
        canonical = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), default=str)
        return sha256(canonical.encode()).hexdigest()

    def approve_dead_letter_replay(
        self,
        tenant_id: str,
        user_id: str,
        run_id: str,
        *,
        ttl_seconds: int = 300,
    ) -> tuple[ReplayApprovalRecord, str]:
        self._require_admin(tenant_id, user_id)
        if ttl_seconds < 1 or ttl_seconds > 3600:
            raise ValueError("approval ttl must be between 1 and 3600 seconds")
        token = uuid4().hex + uuid4().hex
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        with self.engine.begin() as connection:
            owner = connection.execute(
                select(dead_letters.c.tenant_id).where(dead_letters.c.run_id == run_id)
            ).scalar_one_or_none()
            if owner != tenant_id:
                raise KeyError(run_id)
            content_hash = self._dead_letter_content_hash(connection, run_id)
            connection.execute(
                insert(replay_approvals).values(
                    token_hash=sha256(token.encode()).hexdigest(),
                    run_id=run_id,
                    tenant_id=tenant_id,
                    content_hash=content_hash,
                    expires_at=expires_at,
                    used_at=None,
                )
            )
        return ReplayApprovalRecord(
            run_id=run_id, content_hash=content_hash, expires_at=expires_at
        ), token

    def retry_dead_letter(
        self, tenant_id: str, user_id: str, run_id: str, *, approval_token: str
    ) -> RunRecord:
        self._require_admin(tenant_id, user_id)
        with self.engine.begin() as connection:
            letter = connection.execute(
                select(dead_letters).where(
                    dead_letters.c.tenant_id == tenant_id,
                    dead_letters.c.run_id == run_id,
                )
            ).first()
            if letter is None:
                raise KeyError(run_id)
            token_hash = sha256(approval_token.encode()).hexdigest()
            approval = connection.execute(
                select(replay_approvals).where(
                    replay_approvals.c.token_hash == token_hash,
                    replay_approvals.c.tenant_id == tenant_id,
                    replay_approvals.c.run_id == run_id,
                )
            ).mappings().first()
            current_hash = self._dead_letter_content_hash(connection, run_id)
            now = datetime.now(UTC)
            if (
                approval is None
                or approval["used_at"] is not None
                or self._as_utc(cast(datetime, approval["expires_at"])) < now
                or approval["content_hash"] != current_hash
            ):
                raise PermissionError("valid content-bound replay approval required")
            consumed = connection.execute(
                update(replay_approvals)
                .where(
                    replay_approvals.c.token_hash == token_hash,
                    replay_approvals.c.used_at.is_(None),
                    replay_approvals.c.content_hash == current_hash,
                    replay_approvals.c.expires_at >= now,
                )
                .values(used_at=now)
            )
            if consumed.rowcount != 1:
                raise PermissionError("replay approval was already consumed or expired")
            connection.execute(delete(dead_letters).where(dead_letters.c.run_id == run_id))
            connection.execute(delete(run_failures).where(run_failures.c.run_id == run_id))
            connection.execute(
                update(runs)
                .where(runs.c.run_id == run_id)
                .values(status="queued", cancel_requested=False)
            )
        try:
            self.queue.push(run_id)
        except Exception:
            pass
        return self.get_run(tenant_id, run_id)

    def backup_sqlite(self, destination: Path) -> Path:
        if self.engine.url.get_backend_name() != "sqlite":
            raise RuntimeError("PostgreSQL backups require pg_dump or managed snapshots")
        source_path = Path(str(self.engine.url.database))
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(source_path) as source, sqlite3.connect(destination) as target:
            source.backup(target)
        return destination

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


class IdentityVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class HMACIdentityVerifier:
    """Local signed-token adapter; production OIDC adapters implement the same protocol."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("identity signing secret must contain at least 32 characters")
        self.secret = secret.encode()

    @staticmethod
    def _encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def issue(self, principal: Principal, *, ttl_seconds: int = 300) -> str:
        payload = json.dumps(
            {
                "tenant_id": principal.tenant_id,
                "user_id": principal.user_id,
                "exp": int(time.time()) + ttl_seconds,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        encoded = self._encode(payload)
        signature = hmac.new(self.secret, encoded.encode(), sha256).digest()
        return f"{encoded}.{self._encode(signature)}"

    def verify(self, token: str) -> Principal:
        try:
            encoded, supplied = token.split(".", 1)
            expected = hmac.new(self.secret, encoded.encode(), sha256).digest()
            if not hmac.compare_digest(expected, self._decode(supplied)):
                raise PermissionError("invalid identity signature")
            payload = json.loads(self._decode(encoded))
            if int(payload["exp"]) < int(time.time()):
                raise PermissionError("identity token expired")
            return Principal(tenant_id=payload["tenant_id"], user_id=payload["user_id"])
        except (
            binascii.Error,
            KeyError,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise PermissionError("invalid identity token") from exc


def enterprise_principal(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> Principal:
    verifier = cast(IdentityVerifier | None, request.app.state.identity_verifier)
    if verifier is not None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="bearer token required")
        try:
            return verifier.verify(authorization.removeprefix("Bearer "))
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    if not x_tenant_id or not x_user_id:
        raise HTTPException(status_code=422, detail="tenant and user headers required")
    return Principal(tenant_id=x_tenant_id, user_id=x_user_id)


EnterprisePrincipalDep = Annotated[Principal, Depends(enterprise_principal)]


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


class ReplayApprovalCreate(BaseModel):
    ttl_seconds: int = Field(default=300, ge=1, le=3600)


class ReplayApprovalResponse(BaseModel):
    approval: ReplayApprovalRecord
    token: str


class DeadLetterRetryRequest(BaseModel):
    approval_token: str = Field(min_length=64, max_length=128)


def create_enterprise_app(
    platform: EnterprisePlatform,
    *,
    identity_verifier: IdentityVerifier | None = None,
) -> FastAPI:
    app = FastAPI(title="Enterprise Agent Platform", version="1.0.0")
    app.state.identity_verifier = identity_verifier

    def forbidden(exc: PermissionError) -> HTTPException:
        return HTTPException(status_code=403, detail=str(exc))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready() -> dict[str, str]:
        with platform.engine.connect() as connection:
            connection.execute(select(1)).scalar_one()
        return {"status": "ready"}

    @app.get("/admin/runs", response_model=list[RunRecord])
    async def admin_runs(
        identity: EnterprisePrincipalDep,
    ) -> list[RunRecord]:
        try:
            return platform.list_runs(identity.tenant_id, identity.user_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/admin/agents", response_model=AgentRecord)
    async def create_agent(
        body: AgentCreate, identity: EnterprisePrincipalDep
    ) -> AgentRecord:
        try:
            return platform.register_agent(
                identity.tenant_id, identity.user_id, body.name, body.kind
            )
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/admin/tools", response_model=ToolRecord)
    async def create_tool(
        body: ToolCreate, identity: EnterprisePrincipalDep
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
        body: SessionCreate, identity: EnterprisePrincipalDep
    ) -> SessionRecord:
        try:
            return platform.create_session(identity.tenant_id, identity.user_id, body.agent_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/runs", response_model=RunRecord)
    async def create_run(
        body: RunCreate, identity: EnterprisePrincipalDep
    ) -> RunRecord:
        try:
            return platform.submit_run(
                identity.tenant_id, identity.user_id, body.session_id, body.prompt
            )
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/worker/process-one", response_model=RunRecord | None)
    async def process_one(
        identity: EnterprisePrincipalDep,
    ) -> RunRecord | None:
        try:
            platform._require_admin(identity.tenant_id, identity.user_id)
            return platform.process_next(tenant_id=identity.tenant_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.get("/runs/{run_id}", response_model=RunRecord)
    async def get_run(
        run_id: str, identity: EnterprisePrincipalDep
    ) -> RunRecord:
        try:
            return platform.get_run(identity.tenant_id, run_id)
        except PermissionError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

    @app.get("/runs/{run_id}/traces", response_model=list[TraceRecord])
    async def get_traces(
        run_id: str, identity: EnterprisePrincipalDep
    ) -> list[TraceRecord]:
        try:
            return platform.list_traces(identity.tenant_id, run_id)
        except PermissionError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

    @app.post("/runs/{run_id}/cancel", response_model=RunRecord)
    async def cancel_run(
        run_id: str, identity: EnterprisePrincipalDep
    ) -> RunRecord:
        try:
            return platform.cancel_run(identity.tenant_id, identity.user_id, run_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/admin/dead-letters", response_model=list[DeadLetterRecord])
    async def get_dead_letters(
        identity: EnterprisePrincipalDep,
    ) -> list[DeadLetterRecord]:
        try:
            return platform.list_dead_letters(identity.tenant_id, identity.user_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.post("/admin/dead-letters/{run_id}/retry", response_model=RunRecord)
    async def retry_dead_letter(
        run_id: str, body: DeadLetterRetryRequest, identity: EnterprisePrincipalDep
    ) -> RunRecord:
        try:
            return platform.retry_dead_letter(
                identity.tenant_id,
                identity.user_id,
                run_id,
                approval_token=body.approval_token,
            )
        except PermissionError as exc:
            raise forbidden(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="dead letter not found") from exc

    @app.post(
        "/admin/dead-letters/{run_id}/approval",
        response_model=ReplayApprovalResponse,
    )
    async def approve_dead_letter_replay(
        run_id: str,
        body: ReplayApprovalCreate,
        identity: EnterprisePrincipalDep,
    ) -> ReplayApprovalResponse:
        try:
            approval, token = platform.approve_dead_letter_replay(
                identity.tenant_id,
                identity.user_id,
                run_id,
                ttl_seconds=body.ttl_seconds,
            )
            return ReplayApprovalResponse(approval=approval, token=token)
        except PermissionError as exc:
            raise forbidden(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="dead letter not found") from exc

    @app.post("/admin/runs/{run_id}/evaluations", response_model=EvaluationRecord)
    async def evaluate_run(
        run_id: str, identity: EnterprisePrincipalDep
    ) -> EvaluationRecord:
        try:
            return platform.evaluate_run(identity.tenant_id, identity.user_id, run_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc

    @app.get("/metrics")
    async def metrics(identity: EnterprisePrincipalDep) -> Response:
        try:
            platform._require_admin(identity.tenant_id, identity.user_id)
        except PermissionError as exc:
            raise forbidden(exc) from exc
        runs_count = len(platform.list_runs(identity.tenant_id, identity.user_id))
        dead_count = len(platform.list_dead_letters(identity.tenant_id, identity.user_id))
        body = (
            f'agent_platform_runs{{tenant="{identity.tenant_id}"}} {runs_count}\n'
            f'agent_platform_dead_letters{{tenant="{identity.tenant_id}"}} {dead_count}\n'
        )
        return Response(content=body, media_type="text/plain; version=0.0.4")

    return app
