from browser_safety_lab.domain import Action, Approval, BrowserRuntime, Policy
from browser_safety_lab.providers import FakeExpensePage


def _action() -> Action:
    return Action("click", "button", "提交审批", "awaiting_approval", "expense-1")


def test_external_write_requires_content_bound_approval_and_reobservation() -> None:
    page = FakeExpensePage()
    runtime = BrowserRuntime(page, Policy("employee-42", "https://expense.test/"))

    assert runtime.execute(_action()).status == "approval_required"
    result = runtime.execute(_action(), Approval.issue(page.observe(), _action()))

    assert result.status == "completed"
    assert result.after_revision == result.before_revision + 1
    assert page.business_status == "awaiting_approval"


def test_duplicate_submission_is_suppressed_by_business_key() -> None:
    page = FakeExpensePage()
    runtime = BrowserRuntime(page, Policy("employee-42", "https://expense.test/"))
    runtime.execute(_action(), Approval.issue(page.observe(), _action()))

    result = runtime.execute(_action(), Approval.issue(page.observe(), _action()))

    assert result.status == "duplicate_suppressed"
