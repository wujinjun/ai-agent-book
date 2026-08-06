"""Fake clock and SQLite persistence adapter."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from long_term_memory.domain import MemoryRecord


@dataclass
class FakeClock:
    current: datetime

    def now(self) -> datetime:
        return self.current

    def advance(self, duration: timedelta) -> None:
        self.current += duration


class SQLiteMemoryStore:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT NOT NULL,
                explicit INTEGER NOT NULL,
                confidence REAL NOT NULL,
                version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                deleted_at TEXT
            )
            """
        )
        self.connection.commit()

    @staticmethod
    def _record(row: tuple[object, ...]) -> MemoryRecord:
        confidence = row[7]
        version = row[8]
        if not isinstance(confidence, int | float) or not isinstance(version, int):
            raise ValueError("数据库中的 confidence/version 类型非法")
        return MemoryRecord(
            memory_id=str(row[0]),
            tenant_id=str(row[1]),
            user_id=str(row[2]),
            key=str(row[3]),
            value=str(row[4]),
            source=str(row[5]),
            explicit=bool(row[6]),
            confidence=float(confidence),
            version=version,
            created_at=datetime.fromisoformat(str(row[9])),
            expires_at=datetime.fromisoformat(str(row[10])),
        )

    def latest(self, tenant_id: str, user_id: str, key: str) -> MemoryRecord | None:
        row = self.connection.execute(
            """SELECT memory_id, tenant_id, user_id, key, value, source, explicit,
                      confidence, version, created_at, expires_at
               FROM memories WHERE tenant_id=? AND user_id=? AND key=?
               ORDER BY version DESC LIMIT 1""",
            (tenant_id, user_id, key),
        ).fetchone()
        return self._record(row) if row is not None else None

    def insert(self, record: MemoryRecord) -> None:
        self.connection.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (
                record.memory_id,
                record.tenant_id,
                record.user_id,
                record.key,
                record.value,
                record.source,
                int(record.explicit),
                record.confidence,
                record.version,
                record.created_at.isoformat(),
                record.expires_at.isoformat(),
            ),
        )
        self.connection.commit()

    def tombstone_key(self, tenant_id: str, user_id: str, key: str, now: datetime) -> None:
        self.connection.execute(
            """UPDATE memories SET deleted_at=?
               WHERE tenant_id=? AND user_id=? AND key=? AND deleted_at IS NULL""",
            (now.isoformat(), tenant_id, user_id, key),
        )
        self.connection.commit()

    def visible(self, tenant_id: str, user_id: str, now: datetime) -> list[MemoryRecord]:
        rows = self.connection.execute(
            """SELECT memory_id, tenant_id, user_id, key, value, source, explicit,
                      confidence, version, created_at, expires_at
               FROM memories WHERE tenant_id=? AND user_id=? AND deleted_at IS NULL
                 AND expires_at>? ORDER BY key""",
            (tenant_id, user_id, now.isoformat()),
        ).fetchall()
        return [self._record(row) for row in rows]

    def tombstone_user(self, tenant_id: str, user_id: str, now: datetime) -> int:
        cursor = self.connection.execute(
            """UPDATE memories SET deleted_at=?
               WHERE tenant_id=? AND user_id=? AND deleted_at IS NULL""",
            (now.isoformat(), tenant_id, user_id),
        )
        self.connection.commit()
        return cursor.rowcount

    def purge_tombstones(self) -> int:
        cursor = self.connection.execute("DELETE FROM memories WHERE deleted_at IS NOT NULL")
        self.connection.commit()
        return cursor.rowcount

    def raw_values_for_user(self, tenant_id: str, user_id: str) -> list[str]:
        rows = self.connection.execute(
            "SELECT value FROM memories WHERE tenant_id=? AND user_id=?",
            (tenant_id, user_id),
        ).fetchall()
        return [str(row[0]) for row in rows]
