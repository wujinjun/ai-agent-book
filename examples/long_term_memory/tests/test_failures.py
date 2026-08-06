from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from long_term_memory.domain import (
    CrossTenantDenied,
    MemoryCandidate,
    MemoryRejected,
    MemoryService,
)
from long_term_memory.providers import FakeClock, SQLiteMemoryStore


def make_service(tmp_path: Path) -> MemoryService:
    return MemoryService(
        SQLiteMemoryStore(tmp_path / "memory.db"),
        FakeClock(datetime(2026, 8, 6, tzinfo=UTC)),
    )


def test_inferred_memory_requires_explicit_write_policy(tmp_path: Path) -> None:
    memory = make_service(tmp_path)
    candidate = MemoryCandidate(
        "preference", "maybe short", "inference", False, timedelta(days=7), 0.99
    )

    with pytest.raises(MemoryRejected, match="inferred_not_allowed"):
        memory.write(tenant_id="acme", user_id="u1", candidate=candidate)


def test_inferred_value_cannot_overwrite_explicit_fact(tmp_path: Path) -> None:
    memory = make_service(tmp_path)
    memory.write(
        tenant_id="acme",
        user_id="u1",
        candidate=MemoryCandidate("language", "zh", "user", True, timedelta(days=30)),
    )

    with pytest.raises(MemoryRejected, match="explicit_precedence"):
        memory.write(
            tenant_id="acme",
            user_id="u1",
            candidate=MemoryCandidate(
                "language", "en", "inference", False, timedelta(days=7), 0.99
            ),
            allow_inferred=True,
        )


def test_sensitive_values_and_cross_tenant_access_are_denied(tmp_path: Path) -> None:
    memory = make_service(tmp_path)
    with pytest.raises(MemoryRejected, match="sensitive"):
        memory.write(
            tenant_id="acme",
            user_id="u1",
            candidate=MemoryCandidate(
                "credential", "password=secret", "user", True, timedelta(days=1)
            ),
        )

    memory.write(
        tenant_id="acme",
        user_id="u1",
        candidate=MemoryCandidate("language", "zh", "user", True, timedelta(days=30)),
    )
    with pytest.raises(CrossTenantDenied):
        memory.inspect(tenant_id="other", user_id="u1", owner_tenant_id="acme")
