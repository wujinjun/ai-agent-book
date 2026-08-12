"""In-memory page fixture; it never starts a browser or accesses a network."""

from dataclasses import dataclass, field
from typing import Literal

from browser_safety_lab.domain import Element, Observation


@dataclass(slots=True)
class FakeExpensePage:
    duplicate_button: bool = False
    apply_business_change: bool = True
    subject: str = "employee-42"
    url: str = "https://expense.test/review/ER-2026-001"
    revision: int = 1
    business_status: str = "draft"
    applied_keys: set[str] = field(default_factory=set)

    def observe(self) -> Observation:
        button = Element("button", "提交审批", "submit-primary")
        elements = (
            (button, Element("button", "提交审批", "submit-copy"))
            if self.duplicate_button
            else (button,)
        )
        return Observation(self.url, self.subject, self.revision, elements, self.business_status)

    def click(
        self, element_id: str, idempotency_key: str
    ) -> Literal["applied", "duplicate"]:
        if element_id != "submit-primary":
            raise ValueError("unknown element")
        if idempotency_key in self.applied_keys:
            return "duplicate"
        self.applied_keys.add(idempotency_key)
        self.revision += 1
        if self.apply_business_change:
            self.business_status = "awaiting_approval"
        return "applied"

    def mutate_page(self) -> None:
        self.revision += 1
