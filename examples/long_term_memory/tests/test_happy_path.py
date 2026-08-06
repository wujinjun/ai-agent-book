from datetime import UTC, datetime, timedelta
from pathlib import Path

from long_term_memory.domain import MemoryCandidate, MemoryService
from long_term_memory.providers import FakeClock, SQLiteMemoryStore


def service(tmp_path: Path) -> tuple[MemoryService, FakeClock]:
    clock = FakeClock(datetime(2026, 8, 6, tzinfo=UTC))
    return MemoryService(SQLiteMemoryStore(tmp_path / "memory.db"), clock), clock


def test_explicit_memory_preserves_provenance_and_can_be_inspected(tmp_path: Path) -> None:
    memory, _ = service(tmp_path)
    record = memory.write(
        tenant_id="acme",
        user_id="u1",
        candidate=MemoryCandidate(
            key="python_version",
            value="3.12",
            source="user message 42",
            explicit=True,
            ttl=timedelta(days=30),
        ),
    )

    visible = memory.inspect(tenant_id="acme", user_id="u1")

    assert visible == [record]
    assert visible[0].source == "user message 42"
    assert visible[0].version == 1


def test_explicit_correction_supersedes_inferred_value(tmp_path: Path) -> None:
    memory, _ = service(tmp_path)
    memory.write(
        tenant_id="acme",
        user_id="u1",
        candidate=MemoryCandidate(
            "answer_style", "short", "model inference", False, timedelta(days=7), 0.95
        ),
        allow_inferred=True,
    )

    corrected = memory.write(
        tenant_id="acme",
        user_id="u1",
        candidate=MemoryCandidate(
            "answer_style", "detailed", "user correction", True, timedelta(days=30)
        ),
    )

    assert corrected.version == 2
    assert corrected.explicit is True
    assert memory.export(tenant_id="acme", user_id="u1") == {
        "answer_style": "detailed"
    }


def test_ttl_and_delete_propagation_remove_values(tmp_path: Path) -> None:
    memory, clock = service(tmp_path)
    memory.write(
        tenant_id="acme",
        user_id="u1",
        candidate=MemoryCandidate(
            "temporary", "value", "user", True, timedelta(hours=1)
        ),
    )
    clock.advance(timedelta(hours=2))
    assert memory.inspect(tenant_id="acme", user_id="u1") == []

    memory.write(
        tenant_id="acme",
        user_id="u1",
        candidate=MemoryCandidate("language", "zh", "user", True, timedelta(days=30)),
    )
    memory.delete_user(tenant_id="acme", user_id="u1")
    purged = memory.purge_tombstones()

    assert purged >= 1
    assert memory.store.raw_values_for_user("acme", "u1") == []
    assert all("value" not in event for event in memory.audit_events)
