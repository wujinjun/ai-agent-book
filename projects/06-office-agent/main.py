"""项目 6 入口：用 Fixture 邮件/日历生成日报并展示审批边界。"""

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_agent_book.apps.office_agent import (
    CalendarEvent,
    EmailMessage,
    FixtureCalendarProvider,
    FixtureMailProvider,
    JsonlAuditLog,
    OfficeWorkflow,
)


async def main() -> None:
    now = datetime.now(UTC)
    workflow = OfficeWorkflow(
        FixtureMailProvider(
            [EmailMessage(message_id="m1", sender="ci@example.test", subject="CI", body="通过")]
        ),
        FixtureCalendarProvider(
            [
                CalendarEvent(
                    event_id="e1",
                    title="架构评审",
                    starts_at=now + timedelta(hours=1),
                    ends_at=now + timedelta(hours=2),
                )
            ]
        ),
        JsonlAuditLog(Path(os.getenv("AUDIT_PATH", ".data/office-audit.jsonl"))),
    )
    report = await workflow.prepare_daily_report(now, now + timedelta(days=1))
    result = await workflow.publish(report, None, approval_token=None)
    payload = {"report": report.model_dump(mode="json"), "result": result.model_dump()}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
