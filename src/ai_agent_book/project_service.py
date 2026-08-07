"""Production-shaped service boundary shared by the ten teaching projects.

The module owns transport, persistence, tenancy, idempotency and lifecycle rules.
Project-specific behavior remains behind ``run_project`` or an injected executor.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_agent_book.project_catalog import PROJECTS, ProjectResult, run_project

LOGGER = logging.getLogger(__name__)
RunStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
Executor = Callable[[int, str], ProjectResult]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


class ServiceSettings(BaseModel):
    database_path: Path = Path(".data/project-service.db")
    max_prompt_chars: int = Field(default=20_000, ge=100, le=1_000_000)
    require_idempotency_key: bool = True


class Principal(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    roles: frozenset[str]

    def require(self, role: str) -> None:
        if role not in self.roles and "admin" not in self.roles:
            raise HTTPException(status_code=403, detail=f"missing role: {role}")


class RunCreate(BaseModel):
    prompt: str = Field(min_length=1)
    defer: bool = False


class RunRecord(BaseModel):
    run_id: str
    project_id: int
    tenant_id: str
    user_id: str
    status: RunStatus
    prompt: str
    output: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    trace: list[str] = Field(default_factory=list)
    trace_id: str
    created_at: str
    updated_at: str


class EventRecord(BaseModel):
    sequence: int
    event_type: str
    payload: dict[str, Any]
    created_at: str


class ConflictError(RuntimeError):
    """Raised when an idempotency key is reused for a different payload."""


class RunRepository:
    """Small SQLite repository with per-operation connections and explicit transactions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _migrate(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    tenant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    output TEXT,
                    data_json TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runs_tenant_project
                    ON runs(tenant_id, project_id, created_at);
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    tenant_id TEXT NOT NULL,
                    project_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    PRIMARY KEY (tenant_id, project_id, key)
                );
                CREATE TABLE IF NOT EXISTS run_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            db.execute(
                "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (1, ?)",
                (_now(),),
            )

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            project_id=row["project_id"],
            tenant_id=row["tenant_id"],
            user_id=row["user_id"],
            status=row["status"],
            prompt=row["prompt"],
            output=row["output"],
            data=json.loads(row["data_json"]),
            trace=json.loads(row["trace_json"]),
            trace_id=row["trace_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(
        self,
        project_id: int,
        principal: Principal,
        prompt: str,
        idempotency_key: str,
    ) -> tuple[RunRecord, bool]:
        request_hash = sha256(prompt.encode()).hexdigest()
        with self._connect() as db:
            existing = db.execute(
                """SELECT i.request_hash, r.* FROM idempotency_keys i
                   JOIN runs r ON r.run_id = i.run_id
                   WHERE i.tenant_id=? AND i.project_id=? AND i.key=?""",
                (principal.tenant_id, project_id, idempotency_key),
            ).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ConflictError("idempotency key reused with different prompt")
                return self._row_to_run(existing), False

            run_id = str(uuid4())
            now = _now()
            trace_input = f"{principal.tenant_id}:{project_id}:{run_id}"
            trace_id = sha256(trace_input.encode()).hexdigest()[:24]
            db.execute(
                """INSERT INTO runs VALUES (?, ?, ?, ?, 'queued', ?, NULL, '{}', '[]', ?, ?, ?)""",
                (
                    run_id,
                    project_id,
                    principal.tenant_id,
                    principal.user_id,
                    prompt,
                    trace_id,
                    now,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO idempotency_keys VALUES (?, ?, ?, ?, ?)",
                (principal.tenant_id, project_id, idempotency_key, request_hash, run_id),
            )
            self._append_event(db, run_id, "queued", {"trace_id": trace_id})
            self._append_audit(db, principal, "run.created", run_id)
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            assert row is not None
            return self._row_to_run(row), True

    @staticmethod
    def _append_event(
        db: sqlite3.Connection, run_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        db.execute(
            "INSERT INTO run_events(run_id,event_type,payload_json,created_at) VALUES (?,?,?,?)",
            (run_id, event_type, json.dumps(payload, ensure_ascii=False), _now()),
        )

    @staticmethod
    def _append_audit(
        db: sqlite3.Connection, principal: Principal, action: str, resource_id: str
    ) -> None:
        db.execute(
            """INSERT INTO audit_log(tenant_id,user_id,action,resource_id,created_at)
               VALUES (?,?,?,?,?)""",
            (principal.tenant_id, principal.user_id, action, resource_id, _now()),
        )

    def get(self, tenant_id: str, run_id: str) -> RunRecord:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM runs WHERE tenant_id=? AND run_id=?", (tenant_id, run_id)
            ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._row_to_run(row)

    def transition(
        self,
        principal: Principal,
        run_id: str,
        expected: tuple[RunStatus, ...],
        target: RunStatus,
        *,
        output: str | None = None,
        data: dict[str, Any] | None = None,
        trace: list[str] | None = None,
    ) -> RunRecord:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM runs WHERE tenant_id=? AND run_id=?",
                (principal.tenant_id, run_id),
            ).fetchone()
            if row is None:
                raise KeyError(run_id)
            if row["status"] not in expected:
                raise ConflictError(f"cannot transition {row['status']} to {target}")
            db.execute(
                """UPDATE runs SET status=?, output=COALESCE(?,output),
                   data_json=COALESCE(?,data_json), trace_json=COALESCE(?,trace_json), updated_at=?
                   WHERE run_id=?""",
                (
                    target,
                    output,
                    json.dumps(data, ensure_ascii=False) if data is not None else None,
                    json.dumps(trace, ensure_ascii=False) if trace is not None else None,
                    _now(),
                    run_id,
                ),
            )
            self._append_event(db, run_id, target, {"status": target})
            self._append_audit(db, principal, f"run.{target}", run_id)
            updated = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            assert updated is not None
            return self._row_to_run(updated)

    def events(self, tenant_id: str, run_id: str, after: int = 0) -> list[EventRecord]:
        self.get(tenant_id, run_id)
        with self._connect() as db:
            rows = db.execute(
                """SELECT sequence,event_type,payload_json,created_at FROM run_events
                   WHERE run_id=? AND sequence>? ORDER BY sequence""",
                (run_id, after),
            ).fetchall()
        return [
            EventRecord(
                sequence=row["sequence"],
                event_type=row["event_type"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def audit_count(self, tenant_id: str) -> int:
        with self._connect() as db:
            row = db.execute(
                "SELECT COUNT(*) AS count FROM audit_log WHERE tenant_id=?", (tenant_id,)
            ).fetchone()
        return int(row["count"] if row else 0)


class ProjectService:
    def __init__(
        self,
        project_id: int,
        repository: RunRepository,
        executor: Executor = run_project,
    ) -> None:
        if project_id not in PROJECTS:
            raise ValueError(f"unknown project: {project_id}")
        self.project_id = project_id
        self.repository = repository
        self.executor = executor

    def execute(self, principal: Principal, run_id: str) -> RunRecord:
        running = self.repository.transition(principal, run_id, ("queued",), "running")
        try:
            result = self.executor(self.project_id, running.prompt)
        except Exception as exc:
            LOGGER.error(
                "project run failed",
                extra={"run_id": run_id, "error_type": type(exc).__name__},
            )
            return self.repository.transition(
                principal,
                run_id,
                ("running",),
                "failed",
                data={"error_type": type(exc).__name__},
            )
        return self.repository.transition(
            principal,
            run_id,
            ("running",),
            "succeeded",
            output=result.output,
            data=result.data,
            trace=list(result.trace),
        )


def _principal(
    tenant_id: str = Header(alias="X-Tenant-ID", min_length=1),
    user_id: str = Header(alias="X-User-ID", min_length=1),
    roles: str = Header(default="project:run", alias="X-Roles"),
) -> Principal:
    return Principal(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=frozenset(role.strip() for role in roles.split(",") if role.strip()),
    )


PrincipalDep = Annotated[Principal, Depends(_principal)]


def create_project_app(
    project_id: int,
    *,
    settings: ServiceSettings | None = None,
    executor: Executor = run_project,
) -> FastAPI:
    """Create a project-scoped API with a durable, replayable run lifecycle."""
    config = settings or ServiceSettings()
    repository = RunRepository(config.database_path)
    service = ProjectService(project_id, repository, executor)
    definition = PROJECTS[project_id]
    app = FastAPI(title=definition.title, version="1.0.0")
    app.state.project_service = service

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready() -> dict[str, Any]:
        with repository._connect() as db:
            db.execute("SELECT 1").fetchone()
        return {"status": "ready", "project_id": project_id}

    @app.post("/v1/runs", response_model=RunRecord)
    async def create_run(
        request: RunCreate,
        response: Response,
        principal: PrincipalDep,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> RunRecord:
        principal.require("project:run")
        if len(request.prompt) > config.max_prompt_chars:
            raise HTTPException(status_code=413, detail="prompt budget exceeded")
        if config.require_idempotency_key and not idempotency_key:
            raise HTTPException(status_code=400, detail="Idempotency-Key required")
        key = idempotency_key or str(uuid4())
        try:
            run, created = repository.create(project_id, principal, request.prompt, key)
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        if created and not request.defer:
            run = service.execute(principal, run.run_id)
        return run

    @app.get("/v1/runs/{run_id}", response_model=RunRecord)
    async def get_run(run_id: str, principal: PrincipalDep) -> RunRecord:
        try:
            return repository.get(principal.tenant_id, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

    @app.post("/v1/runs/{run_id}/execute", response_model=RunRecord)
    async def execute_run(run_id: str, principal: PrincipalDep) -> RunRecord:
        principal.require("project:run")
        try:
            return service.execute(principal, run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/v1/runs/{run_id}/cancel", response_model=RunRecord)
    async def cancel_run(run_id: str, principal: PrincipalDep) -> RunRecord:
        principal.require("project:run")
        try:
            return repository.transition(
                principal, run_id, ("queued", "running"), "cancelled"
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/v1/runs/{run_id}/events")
    async def stream_events(
        run_id: str,
        principal: PrincipalDep,
        after: int = Query(default=0, ge=0),
    ) -> StreamingResponse:
        try:
            events = repository.events(principal.tenant_id, run_id, after)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

        def generate() -> Iterator[str]:
            for event in events:
                payload = json.dumps(event.model_dump(), ensure_ascii=False)
                yield f"id: {event.sequence}\nevent: {event.event_type}\ndata: {payload}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.get("/metrics")
    async def metrics(principal: PrincipalDep) -> Response:
        principal.require("project:observe")
        count = repository.audit_count(principal.tenant_id)
        body = f"agent_project_audit_events{{project_id=\"{project_id}\"}} {count}\n"
        return Response(content=body, media_type="text/plain; version=0.0.4")

    return app
