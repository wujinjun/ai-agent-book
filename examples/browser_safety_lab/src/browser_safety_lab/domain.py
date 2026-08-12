"""Provider-neutral observation, policy, approval and verification boundaries."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class Element:
    role: str
    name: str
    element_id: str


@dataclass(frozen=True, slots=True)
class Observation:
    url: str
    subject: str
    revision: int
    elements: tuple[Element, ...]
    business_status: str

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "url": self.url,
                "subject": self.subject,
                "revision": self.revision,
                "elements": [
                    (item.role, item.name, item.element_id) for item in self.elements
                ],
                "business_status": self.business_status,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Action:
    kind: Literal["click"]
    role: str
    name: str
    expected_status: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class Approval:
    observation_fingerprint: str
    action_digest: str

    @classmethod
    def issue(cls, observation: Observation, action: Action) -> Approval:
        return cls(observation.fingerprint, action_digest(action))


@dataclass(frozen=True, slots=True)
class Outcome:
    status: Literal[
        "completed",
        "approval_required",
        "ambiguous_target",
        "stale_approval",
        "duplicate_suppressed",
        "verification_failed",
        "policy_denied",
    ]
    detail: str
    before_revision: int
    after_revision: int


def action_digest(action: Action) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "kind": action.kind,
                "role": action.role,
                "name": action.name,
                "expected_status": action.expected_status,
                "idempotency_key": action.idempotency_key,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


class PagePort(Protocol):
    def observe(self) -> Observation: ...

    def click(self, element_id: str, idempotency_key: str) -> Literal["applied", "duplicate"]: ...


@dataclass(frozen=True, slots=True)
class Policy:
    allowed_subject: str
    allowed_url_prefix: str

    def permits(self, observation: Observation) -> bool:
        return observation.subject == self.allowed_subject and observation.url.startswith(
            self.allowed_url_prefix
        )


class BrowserRuntime:
    """The model proposes an action; this runtime owns authority and side effects."""

    def __init__(self, page: PagePort, policy: Policy) -> None:
        self._page = page
        self._policy = policy

    def execute(self, action: Action, approval: Approval | None = None) -> Outcome:
        before = self._page.observe()
        if not self._policy.permits(before):
            return Outcome(
                "policy_denied",
                "subject_or_origin_not_allowed",
                before.revision,
                before.revision,
            )

        matches = [
            item
            for item in before.elements
            if item.role == action.role and item.name == action.name
        ]
        if len(matches) != 1:
            return Outcome(
                "ambiguous_target",
                f"semantic_matches={len(matches)}",
                before.revision,
                before.revision,
            )

        if approval is None:
            return Outcome(
                "approval_required",
                before.fingerprint,
                before.revision,
                before.revision,
            )
        if approval is not None and (
            not hmac.compare_digest(approval.observation_fingerprint, before.fingerprint)
            or not hmac.compare_digest(approval.action_digest, action_digest(action))
        ):
            return Outcome(
                "stale_approval",
                "page_or_action_changed",
                before.revision,
                before.revision,
            )

        result = self._page.click(matches[0].element_id, action.idempotency_key)
        after = self._page.observe()  # Driver success is not business success.
        if result == "duplicate":
            return Outcome(
                "duplicate_suppressed",
                after.business_status,
                before.revision,
                after.revision,
            )
        if after.business_status != action.expected_status:
            return Outcome(
                "verification_failed",
                after.business_status,
                before.revision,
                after.revision,
            )
        return Outcome("completed", after.business_status, before.revision, after.revision)
