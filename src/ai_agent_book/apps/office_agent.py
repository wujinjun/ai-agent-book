"""项目 6：邮件、日历、日报、审批、Webhook 发布与持久审计。"""

from __future__ import annotations

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
    status: Literal["approval_required", "published"]
    external_id: str | None = None


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
    async def publish(self, title: str, markdown: str) -> str: ...


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


class WebhookPublisher:
    """适配飞书自定义机器人或内部办公 Webhook 的最小 HTTP 边界。"""

    def __init__(self, url: str, *, client: httpx.AsyncClient | None = None) -> None:
        self.url = url
        self.client = client

    async def publish(self, title: str, markdown: str) -> str:
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=10)
        try:
            response = await client.post(
                self.url,
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
    ) -> None:
        self.mail = mail
        self.calendar = calendar
        self.audit = audit
        self.approvals: dict[str, str] = {}

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

    def approve(self, report: DailyReport, *, approver: str) -> str:
        token = sha256(
            f"{report.report_id}:{report.digest}:{approver}:{uuid4()}".encode()
        ).hexdigest()
        self.approvals[report.report_id] = token
        self._audit("approved", report.report_id, approver, {"digest": report.digest})
        return token

    async def publish(
        self,
        report: DailyReport,
        publisher: Publisher | None,
        *,
        approval_token: str | None,
    ) -> PublishResult:
        if not approval_token or self.approvals.get(report.report_id) != approval_token:
            self._audit("publish_blocked", report.report_id, "agent")
            return PublishResult(status="approval_required")
        if publisher is None:
            external_id = "mock-published"
        else:
            external_id = await publisher.publish("自动办公日报", report.markdown)
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
