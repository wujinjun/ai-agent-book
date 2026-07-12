from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_agent_book.apps.office_agent import (
    FixtureCalendarProvider,
    FixtureMailProvider,
    JsonlAuditLog,
    OfficeWorkflow,
)


@pytest.mark.asyncio
async def test_publish_requires_approval(tmp_path: Path) -> None:
    workflow = OfficeWorkflow(
        FixtureMailProvider([]), FixtureCalendarProvider([]), JsonlAuditLog(tmp_path / "audit")
    )
    now = datetime.now(UTC)
    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    assert (await workflow.publish(report, None, approval_token=None)).status == "approval_required"
