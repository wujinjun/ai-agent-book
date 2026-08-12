"""项目 6：邮件、日历、日报、审批、Webhook 发布与持久审计。"""

from __future__ import annotations

import hmac
import secrets
import sqlite3
import time
from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    message_id: str
    sender: str
    subject: str
    body: str


class CalendarEvent(BaseModel):
    event_id: str
    title: str
    starts_at: datetime
    ends_at: datetime


class DailyReport(BaseModel):
    report_id: str
    markdown: str
    digest: str
    period_start: datetime
    period_end: datetime


class PublishResult(BaseModel):
    status: Literal["approval_required", "published", "failed"]
    external_id: str | None = None
    retryable: bool = False


class AuditEntry(BaseModel):
    timestamp: datetime
    action: str
    resource_id: str
    actor: str
    details: dict[str, str] = Field(default_factory=dict)


class MailProvider(Protocol):
    async def list_messages(self, start: datetime, end: datetime) -> Sequence[EmailMessage]: ...


class CalendarProvider(Protocol):
    async def list_events(self, start: datetime, end: datetime) -> Sequence[CalendarEvent]: ...


class Publisher(Protocol):
    async def publish(self, title: str, markdown: str, *, idempotency_key: str) -> str: ...


class FixtureMailProvider:
    def __init__(self, messages: Sequence[EmailMessage]) -> None:
        self.messages = messages

    async def list_messages(self, start: datetime, end: datetime) -> Sequence[EmailMessage]:
        return self.messages


class FixtureCalendarProvider:
    def __init__(self, events: Sequence[CalendarEvent]) -> None:
        self.events = events

    async def list_events(self, start: datetime, end: datetime) -> Sequence[CalendarEvent]:
        return [event for event in self.events if start <= event.starts_at < end]


class JsonlAuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: AuditEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")

    def read(self) -> list[AuditEntry]:
        if not self.path.exists():
            return []
        return [AuditEntry.model_validate_json(line) for line in self.path.read_text().splitlines()]


class ApprovalOutboxStore:
    """持久化内容审批和幂等 Outbox；SQLite 适合单机教学与恢复演练。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS approval (
                    token_hash TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    report_digest TEXT NOT NULL,
                    target TEXT NOT NULL,
                    approver TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    idempotency_key TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    report_digest TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    external_id TEXT,
                    last_error TEXT,
                    lease_until INTEGER,
                    updated_at INTEGER NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _token_hash(token: str) -> str:
        return sha256(token.encode()).hexdigest()

    @staticmethod
    def idempotency_key(report: DailyReport, target: str) -> str:
        payload = f"office-publish:{report.report_id}:{report.digest}:{target}"
        return sha256(payload.encode()).hexdigest()

    def issue(
        self,
        report: DailyReport,
        *,
        target: str,
        approver: str,
        ttl_seconds: int = 900,
        now: int | None = None,
    ) -> str:
        if ttl_seconds < 1:
            raise ValueError("approval ttl must be positive")
        _validate_report_digest(report)
        issued_at = int(time.time()) if now is None else now
        token = secrets.token_urlsafe(32)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO approval
                (token_hash, report_id, report_digest, target, approver, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    self._token_hash(token),
                    report.report_id,
                    report.digest,
                    target,
                    approver,
                    issued_at + ttl_seconds,
                    issued_at,
                ),
            )
        return token

    def claim(
        self,
        report: DailyReport,
        *,
        target: str,
        approval_token: str,
        lease_seconds: int = 30,
        max_attempts: int = 3,
        now: int | None = None,
    ) -> tuple[str, str | None]:
        """返回 ``(状态, external_id)``；状态为 claimed/published/busy/exhausted。"""
        _validate_report_digest(report)
        current = int(time.time()) if now is None else now
        key = self.idempotency_key(report, target)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            approval = connection.execute(
                "SELECT * FROM approval WHERE token_hash = ?",
                (self._token_hash(approval_token),),
            ).fetchone()
            if approval is None:
                raise PermissionError("approval token is unknown")
            bound = (
                hmac.compare_digest(str(approval["report_id"]), report.report_id)
                and hmac.compare_digest(str(approval["report_digest"]), report.digest)
                and hmac.compare_digest(str(approval["target"]), target)
            )
            if not bound:
                raise PermissionError("approval is not bound to this content and target")
            if int(approval["expires_at"]) < current:
                raise PermissionError("approval has expired")

            connection.execute(
                """INSERT OR IGNORE INTO outbox
                (idempotency_key, report_id, report_digest, target, status, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?)""",
                (key, report.report_id, report.digest, target, current),
            )
            item = connection.execute(
                "SELECT * FROM outbox WHERE idempotency_key = ?", (key,)
            ).fetchone()
            assert item is not None
            if item["status"] == "published":
                return "published", str(item["external_id"])
            if item["status"] == "delivering" and int(item["lease_until"] or 0) >= current:
                return "busy", None
            if int(item["attempts"]) >= max_attempts:
                return "exhausted", None
            connection.execute(
                """UPDATE outbox SET status = 'delivering', attempts = attempts + 1,
                lease_until = ?, updated_at = ? WHERE idempotency_key = ?""",
                (current + lease_seconds, current, key),
            )
        return "claimed", None

    def mark_published(self, key: str, external_id: str, *, now: int | None = None) -> None:
        current = int(time.time()) if now is None else now
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE outbox SET status = 'published', external_id = ?, last_error = NULL,
                lease_until = NULL, updated_at = ?
                WHERE idempotency_key = ? AND status = 'delivering'""",
                (external_id, current, key),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("outbox item is not claimed")

    def mark_failed(self, key: str, error: str, *, now: int | None = None) -> None:
        current = int(time.time()) if now is None else now
        safe_error = error[:500]
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE outbox SET status = 'failed', last_error = ?, lease_until = NULL,
                updated_at = ? WHERE idempotency_key = ? AND status = 'delivering'""",
                (safe_error, current, key),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("outbox item is not claimed")

    def get_outbox(self, key: str) -> dict[str, str | int | None] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM outbox WHERE idempotency_key = ?", (key,)
            ).fetchone()
        return dict(row) if row else None


def _validate_report_digest(report: DailyReport) -> None:
    current = sha256(report.markdown.encode()).hexdigest()
    if not hmac.compare_digest(current, report.digest):
        raise PermissionError("report content changed after digest creation")


class WebhookPublisher:
    """适配飞书自定义机器人或内部办公 Webhook 的最小 HTTP 边界。"""

    def __init__(self, url: str, *, client: httpx.AsyncClient | None = None) -> None:
        self.url = url
        self.client = client

    async def publish(self, title: str, markdown: str, *, idempotency_key: str) -> str:
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=10)
        try:
            response = await client.post(
                self.url,
                headers={"Idempotency-Key": idempotency_key},
                json={"msg_type": "text", "content": {"text": f"{title}\n{markdown}"}},
            )
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("message_id") or payload.get("id") or "webhook-accepted")
        finally:
            if owns_client:
                await client.aclose()


class OfficeWorkflow:
    def __init__(
        self,
        mail: MailProvider,
        calendar: CalendarProvider,
        audit: JsonlAuditLog,
        state: ApprovalOutboxStore | None = None,
    ) -> None:
        self.mail = mail
        self.calendar = calendar
        self.audit = audit
        self.state = state or ApprovalOutboxStore(audit.path.with_suffix(".sqlite3"))

    async def prepare_daily_report(self, start: datetime, end: datetime) -> DailyReport:
        if end <= start:
            raise ValueError("end must be after start")
        messages = await self.mail.list_messages(start, end)
        events = await self.calendar.list_events(start, end)
        sections = ["# 日报", "", "## 邮件摘要"]
        if messages:
            sections.extend(
                f"- **{message.subject}**（{message.sender}）：{message.body.strip()[:300]}"
                for message in messages
            )
        else:
            sections.append("- 本时段没有邮件。")
        sections.extend(["", "## 日程"])
        if events:
            sections.extend(
                f"- {event.starts_at.isoformat()}—{event.ends_at.isoformat()}：{event.title}"
                for event in events
            )
        else:
            sections.append("- 本时段没有日程。")
        markdown = "\n".join(sections)
        report = DailyReport(
            report_id=str(uuid4()),
            markdown=markdown,
            digest=sha256(markdown.encode()).hexdigest(),
            period_start=start,
            period_end=end,
        )
        self._audit("report_prepared", report.report_id, "agent")
        return report

    def approve(
        self,
        report: DailyReport,
        *,
        approver: str,
        target: str = "daily-report",
        ttl_seconds: int = 900,
        now: int | None = None,
    ) -> str:
        token = self.state.issue(
            report,
            target=target,
            approver=approver,
            ttl_seconds=ttl_seconds,
            now=now,
        )
        self._audit(
            "approved",
            report.report_id,
            approver,
            {"digest": report.digest, "target": target},
        )
        return token

    async def publish(
        self,
        report: DailyReport,
        publisher: Publisher | None,
        *,
        approval_token: str | None,
        target: str = "daily-report",
        now: int | None = None,
    ) -> PublishResult:
        if not approval_token:
            self._audit("publish_blocked", report.report_id, "agent", {"reason": "missing"})
            return PublishResult(status="approval_required")
        try:
            claim, external_id = self.state.claim(
                report, target=target, approval_token=approval_token, now=now
            )
        except PermissionError as exc:
            self._audit(
                "publish_blocked", report.report_id, "agent", {"reason": str(exc), "target": target}
            )
            return PublishResult(status="approval_required")
        if claim == "published":
            return PublishResult(status="published", external_id=external_id)
        if claim in {"busy", "exhausted"}:
            return PublishResult(status="failed", retryable=claim == "busy")

        key = self.state.idempotency_key(report, target)
        if publisher is None:
            external_id = "mock-published"
        else:
            try:
                external_id = await publisher.publish(
                    "自动办公日报", report.markdown, idempotency_key=key
                )
            except (httpx.HTTPError, TimeoutError, OSError, ValueError) as exc:
                self.state.mark_failed(key, type(exc).__name__)
                self._audit(
                    "publish_failed",
                    report.report_id,
                    "agent",
                    {"error_type": type(exc).__name__, "target": target},
                )
                return PublishResult(status="failed", retryable=True)
        self.state.mark_published(key, external_id)
        self._audit("published", report.report_id, "agent", {"external_id": external_id})
        return PublishResult(status="published", external_id=external_id)

    def _audit(
        self,
        action: str,
        resource_id: str,
        actor: str,
        details: dict[str, str] | None = None,
    ) -> None:
        self.audit.append(
            AuditEntry(
                timestamp=datetime.now().astimezone(),
                action=action,
                resource_id=resource_id,
                actor=actor,
                details=details or {},
            )
        )
