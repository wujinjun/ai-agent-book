from browser_safety_lab.domain import Action, Approval, BrowserRuntime, Policy
from browser_safety_lab.providers import FakeExpensePage


def _action() -> Action:
    return Action("click", "button", "提交审批", "awaiting_approval", "expense-1")


def test_ambiguous_semantic_target_is_not_clicked() -> None:
    page = FakeExpensePage(duplicate_button=True)
    runtime = BrowserRuntime(page, Policy("employee-42", "https://expense.test/"))

    assert runtime.execute(_action()).status == "ambiguous_target"
    assert page.applied_keys == set()


def test_page_change_invalidates_prior_approval() -> None:
    page = FakeExpensePage()
    runtime = BrowserRuntime(page, Policy("employee-42", "https://expense.test/"))
    approval = Approval.issue(page.observe(), _action())
    page.mutate_page()

    assert runtime.execute(_action(), approval).status == "stale_approval"


def test_driver_success_without_business_change_fails_verification() -> None:
    page = FakeExpensePage(apply_business_change=False)
    runtime = BrowserRuntime(page, Policy("employee-42", "https://expense.test/"))

    result = runtime.execute(_action(), Approval.issue(page.observe(), _action()))

    assert result.status == "verification_failed"


def test_subject_and_origin_are_enforced_outside_the_model() -> None:
    page = FakeExpensePage(subject="attacker", url="https://phish.test/")
    runtime = BrowserRuntime(page, Policy("employee-42", "https://expense.test/"))

    assert runtime.execute(_action()).status == "policy_denied"
