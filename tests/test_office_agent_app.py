from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from ai_agent_book.apps.office_agent import (
    CalendarEvent,
    EmailMessage,
    FixtureCalendarProvider,
    FixtureMailProvider,
    JsonlAuditLog,
    OfficeWorkflow,
    WebhookPublisher,
)


@pytest.mark.asyncio
async def test_office_workflow_summarizes_mail_and_calendar_then_requires_approval(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    mail = FixtureMailProvider(
        [EmailMessage(message_id="m1", sender="a@example.test", subject="构建", body="CI 已通过")]
    )
    calendar = FixtureCalendarProvider(
        [
            CalendarEvent(
                event_id="e1",
                title="架构评审",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=2),
            )
        ]
    )
    audit = JsonlAuditLog(tmp_path / "audit.jsonl")
    workflow = OfficeWorkflow(mail, calendar, audit)

    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    blocked = await workflow.publish(report, publisher=None, approval_token=None)
    token = workflow.approve(report, approver="manager@example.test")

    assert "CI 已通过" in report.markdown
    assert "架构评审" in report.markdown
    assert blocked.status == "approval_required"
    assert token
    assert [item.action for item in audit.read()] == [
        "report_prepared",
        "publish_blocked",
        "approved",
    ]


@pytest.mark.asyncio
async def test_webhook_publish_occurs_only_after_content_bound_approval(tmp_path: Path) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"ok": True})

    now = datetime.now(UTC)
    workflow = OfficeWorkflow(
        FixtureMailProvider([]),
        FixtureCalendarProvider([]),
        JsonlAuditLog(tmp_path / "audit.jsonl"),
    )
    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    token = workflow.approve(report, approver="manager")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await workflow.publish(
            report,
            WebhookPublisher("https://office.test/hook", client=client),
            approval_token=token,
        )
    assert result.status == "published"
    assert requests == 1
