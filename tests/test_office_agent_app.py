from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from ai_agent_book.apps.office_agent import (
    ApprovalOutboxStore,
    CalendarEvent,
    EmailMessage,
    FixtureCalendarProvider,
    FixtureMailProvider,
    JsonlAuditLog,
    OfficeWorkflow,
    WebhookPublisher,
)


class FixtureReconciler:
    def __init__(self, receipt: str | None) -> None:
        self.receipt = receipt
        self.keys: list[str] = []

    async def lookup_receipt(self, *, idempotency_key: str) -> str | None:
        self.keys.append(idempotency_key)
        return self.receipt


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
    idempotency_key = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal idempotency_key, requests
        requests += 1
        idempotency_key = request.headers["Idempotency-Key"]
        return httpx.Response(200, json={"message_id": "msg-1"})

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
    assert result.external_id == "msg-1"
    assert requests == 1
    assert len(idempotency_key) == 64


@pytest.mark.asyncio
async def test_approval_and_published_result_survive_restart_without_duplicate_send(
    tmp_path: Path,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"message_id": "durable-1"})

    now = datetime.now(UTC)
    state_path = tmp_path / "office.db"
    audit = JsonlAuditLog(tmp_path / "audit.jsonl")
    first = OfficeWorkflow(
        FixtureMailProvider([]),
        FixtureCalendarProvider([]),
        audit,
        ApprovalOutboxStore(state_path),
    )
    report = await first.prepare_daily_report(now, now + timedelta(days=1))
    token = first.approve(report, approver="manager")

    restarted = OfficeWorkflow(
        FixtureMailProvider([]),
        FixtureCalendarProvider([]),
        audit,
        ApprovalOutboxStore(state_path),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        publisher = WebhookPublisher("https://office.test/hook", client=client)
        first_result = await restarted.publish(report, publisher, approval_token=token)
        duplicate_result = await restarted.publish(report, publisher, approval_token=token)

    assert first_result.external_id == duplicate_result.external_id == "durable-1"
    assert requests == 1


@pytest.mark.asyncio
async def test_changed_content_wrong_target_and_expired_approval_are_blocked(
    tmp_path: Path,
) -> None:
    now = datetime.now(UTC)
    workflow = OfficeWorkflow(
        FixtureMailProvider([]),
        FixtureCalendarProvider([]),
        JsonlAuditLog(tmp_path / "audit.jsonl"),
    )
    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    token = workflow.approve(report, approver="manager", target="team-a", now=100, ttl_seconds=10)

    changed = report.model_copy(update={"markdown": report.markdown + "\n篡改"})
    assert (
        await workflow.publish(changed, None, approval_token=token, target="team-a", now=105)
    ).status == "approval_required"
    assert (
        await workflow.publish(report, None, approval_token=token, target="team-b", now=105)
    ).status == "approval_required"
    assert (
        await workflow.publish(report, None, approval_token=token, target="team-a", now=111)
    ).status == "approval_required"


@pytest.mark.asyncio
async def test_transient_failure_is_persisted_and_retry_recovers(tmp_path: Path) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            raise httpx.ConnectError("temporary", request=request)
        return httpx.Response(200, json={"message_id": "retry-ok"})

    now = datetime.now(UTC)
    store = ApprovalOutboxStore(tmp_path / "office.db")
    workflow = OfficeWorkflow(
        FixtureMailProvider([]),
        FixtureCalendarProvider([]),
        JsonlAuditLog(tmp_path / "audit.jsonl"),
        store,
    )
    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    token = workflow.approve(report, approver="manager")
    key = store.idempotency_key(report, "daily-report")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        publisher = WebhookPublisher("https://office.test/hook", client=client)
        failed = await workflow.publish(report, publisher, approval_token=token)
        item_after_failure = store.get_outbox(key)
        recovered = await workflow.publish(report, publisher, approval_token=token)

    assert failed.status == "failed" and failed.retryable
    assert item_after_failure is not None and item_after_failure["status"] == "failed"
    assert recovered.status == "published" and recovered.external_id == "retry-ok"
    assert requests == 2


@pytest.mark.asyncio
async def test_ambiguous_timeout_is_reconciled_by_remote_receipt(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("response lost after accept", request=request)

    now = datetime.now(UTC)
    store = ApprovalOutboxStore(tmp_path / "office.db")
    workflow = OfficeWorkflow(
        FixtureMailProvider([]),
        FixtureCalendarProvider([]),
        JsonlAuditLog(tmp_path / "audit.jsonl"),
        store,
    )
    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    token = workflow.approve(report, approver="manager")
    reconciler = FixtureReconciler("remote-receipt-1")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await workflow.publish(
            report,
            WebhookPublisher("https://office.test/hook", client=client),
            approval_token=token,
            reconciler=reconciler,
        )

    item = store.get_outbox(store.idempotency_key(report, "daily-report"))
    assert result.status == "published" and result.external_id == "remote-receipt-1"
    assert item is not None and item["status"] == "published"
    assert len(reconciler.keys) == 1


@pytest.mark.asyncio
async def test_unresolved_ambiguous_timeout_requires_manual_reconciliation(
    tmp_path: Path,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        raise httpx.ReadTimeout("unknown remote result", request=request)

    now = datetime.now(UTC)
    store = ApprovalOutboxStore(tmp_path / "office.db")
    workflow = OfficeWorkflow(
        FixtureMailProvider([]),
        FixtureCalendarProvider([]),
        JsonlAuditLog(tmp_path / "audit.jsonl"),
        store,
    )
    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    token = workflow.approve(report, approver="manager")
    reconciler = FixtureReconciler(None)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        publisher = WebhookPublisher("https://office.test/hook", client=client)
        unknown = await workflow.publish(
            report, publisher, approval_token=token, reconciler=reconciler
        )
        repeated = await workflow.publish(
            report, publisher, approval_token=token, reconciler=reconciler
        )

    item = store.get_outbox(store.idempotency_key(report, "daily-report"))
    assert unknown.reconciliation_required and not unknown.retryable
    assert repeated.reconciliation_required and not repeated.retryable
    assert item is not None and item["status"] == "unknown"
    assert requests == 1
