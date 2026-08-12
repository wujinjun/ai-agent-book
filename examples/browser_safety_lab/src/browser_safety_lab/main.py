"""Run the deterministic approval-bound form submission fixture."""

import argparse
import json
from dataclasses import asdict

from browser_safety_lab.domain import Action, Approval, BrowserRuntime, Policy
from browser_safety_lab.providers import FakeExpensePage


def build_report() -> dict[str, object]:
    page = FakeExpensePage()
    runtime = BrowserRuntime(page, Policy("employee-42", "https://expense.test/"))
    action = Action("click", "button", "提交审批", "awaiting_approval", "ER-2026-001:submit")
    pending = runtime.execute(action)
    approval = Approval.issue(page.observe(), action)
    completed = runtime.execute(action, approval)
    duplicate = runtime.execute(action, Approval.issue(page.observe(), action))
    return {
        "pending": asdict(pending),
        "completed": asdict(completed),
        "duplicate": asdict(duplicate),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("expense",), default="expense")
    parser.parse_args()
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
