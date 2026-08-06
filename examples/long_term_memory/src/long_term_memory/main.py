"""Inspect, export or delete an offline governed-memory fixture."""

import argparse
import json
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from long_term_memory.domain import MemoryCandidate, MemoryService
from long_term_memory.providers import FakeClock, SQLiteMemoryStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("preferences",), default="preferences")
    parser.add_argument("--action", choices=("inspect", "export", "delete"), default="inspect")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        service = MemoryService(
            SQLiteMemoryStore(Path(directory) / "memory.db"),
            FakeClock(datetime(2026, 8, 6, tzinfo=UTC)),
        )
        service.write(
            tenant_id="acme",
            user_id="demo",
            candidate=MemoryCandidate(
                "python_version", "3.12", "explicit fixture", True, timedelta(days=30)
            ),
        )
        if args.action == "inspect":
            result: object = [
                asdict(record)
                for record in service.inspect(tenant_id="acme", user_id="demo")
            ]
        elif args.action == "export":
            result = service.export(tenant_id="acme", user_id="demo")
        else:
            service.delete_user(tenant_id="acme", user_id="demo")
            result = {"purged": service.purge_tombstones(), "audit": service.audit_events}
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
