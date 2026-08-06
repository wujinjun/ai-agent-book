"""Write policy, conflict resolution, TTL, export and deletion governance."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol


class MemoryRejected(ValueError):
    pass


class CrossTenantDenied(PermissionError):
    pass


@dataclass(frozen=True)
class MemoryCandidate:
    key: str
    value: str
    source: str
    explicit: bool
    ttl: timedelta
    confidence: float = 1.0


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    tenant_id: str
    user_id: str
    key: str
    value: str
    source: str
    explicit: bool
    confidence: float
    version: int
    created_at: datetime
    expires_at: datetime


class Clock(Protocol):
    def now(self) -> datetime: ...


class MemoryStore(Protocol):
    def latest(self, tenant_id: str, user_id: str, key: str) -> MemoryRecord | None: ...

    def insert(self, record: MemoryRecord) -> None: ...

    def tombstone_key(self, tenant_id: str, user_id: str, key: str, now: datetime) -> None: ...

    def visible(self, tenant_id: str, user_id: str, now: datetime) -> list[MemoryRecord]: ...

    def tombstone_user(self, tenant_id: str, user_id: str, now: datetime) -> int: ...

    def purge_tombstones(self) -> int: ...

    def raw_values_for_user(self, tenant_id: str, user_id: str) -> list[str]: ...


SENSITIVE = (
    re.compile(r"(?i)password\s*[:=]"),
    re.compile(r"(?i)(?:api[_-]?key|secret)\s*[:=]"),
    re.compile(r"\b\d{16}\b"),
)


class MemoryService:
    def __init__(self, store: MemoryStore, clock: Clock) -> None:
        self.store = store
        self.clock = clock
        self.audit_events: list[dict[str, object]] = []

    def write(
        self,
        *,
        tenant_id: str,
        user_id: str,
        candidate: MemoryCandidate,
        allow_inferred: bool = False,
    ) -> MemoryRecord:
        if not candidate.key or not candidate.value or not candidate.source:
            raise MemoryRejected("missing_required_field")
        if candidate.ttl <= timedelta(0):
            raise MemoryRejected("invalid_ttl")
        if any(pattern.search(candidate.value) for pattern in SENSITIVE):
            raise MemoryRejected("sensitive_value")
        if not candidate.explicit and (
            not allow_inferred or candidate.confidence < 0.9
        ):
            raise MemoryRejected("inferred_not_allowed")

        previous = self.store.latest(tenant_id, user_id, candidate.key)
        if previous is not None and previous.explicit and not candidate.explicit:
            raise MemoryRejected("explicit_precedence")
        version = 1 if previous is None else previous.version + 1
        now = self.clock.now()
        if previous is not None:
            self.store.tombstone_key(tenant_id, user_id, candidate.key, now)
        memory_id = f"{tenant_id}:{user_id}:{candidate.key}:v{version}"
        record = MemoryRecord(
            memory_id=memory_id,
            tenant_id=tenant_id,
            user_id=user_id,
            key=candidate.key,
            value=candidate.value,
            source=candidate.source,
            explicit=candidate.explicit,
            confidence=candidate.confidence,
            version=version,
            created_at=now,
            expires_at=now + candidate.ttl,
        )
        self.store.insert(record)
        self.audit_events.append(
            {"event": "memory.written", "memory_id": memory_id, "key": candidate.key}
        )
        return record

    def inspect(
        self,
        *,
        tenant_id: str,
        user_id: str,
        owner_tenant_id: str | None = None,
    ) -> list[MemoryRecord]:
        if owner_tenant_id is not None and tenant_id != owner_tenant_id:
            raise CrossTenantDenied("cross_tenant_denied")
        return self.store.visible(tenant_id, user_id, self.clock.now())

    def export(self, *, tenant_id: str, user_id: str) -> dict[str, str]:
        return {
            record.key: record.value
            for record in self.inspect(tenant_id=tenant_id, user_id=user_id)
        }

    def delete_user(self, *, tenant_id: str, user_id: str) -> int:
        count = self.store.tombstone_user(tenant_id, user_id, self.clock.now())
        self.audit_events.append(
            {"event": "memory.user_deleted", "tenant_id": tenant_id, "count": count}
        )
        return count

    def purge_tombstones(self) -> int:
        count = self.store.purge_tombstones()
        self.audit_events.append({"event": "memory.tombstones_purged", "count": count})
        return count
