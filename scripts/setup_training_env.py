#!/usr/bin/env python3
"""Create a deterministic, offline-first training workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "training" / "fixtures"


class FixtureRecord(BaseModel):
    """Minimum contract shared by all JSONL training records."""

    model_config = ConfigDict(extra="allow")

    id: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_jsonl(path: Path) -> int:
    ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = FixtureRecord.model_validate_json(line)
        if record.id in ids:
            raise ValueError(f"{path.name}:{line_number}: duplicate id {record.id}")
        ids.add(record.id)
    if not ids:
        raise ValueError(f"{path.name}: no records")
    return len(ids)


def _validate_json(path: Path) -> int:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("scenarios"), list):
        raise ValueError(f"{path.name}: expected an object with scenarios")
    return len(payload["scenarios"])


def build_workspace(target: Path, *, force: bool = False) -> dict[str, Any]:
    """Copy validated fixtures and return a content-addressed manifest."""

    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"target is not empty: {target}; pass --force to replace it")
    if target.exists() and force:
        shutil.rmtree(target)
    fixture_target = target / "fixtures"
    submission_target = target / "submissions"
    fixture_target.mkdir(parents=True, exist_ok=True)
    submission_target.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    for source in sorted(FIXTURE_ROOT.iterdir()):
        if source.suffix == ".jsonl":
            records = _validate_jsonl(source)
        elif source.suffix == ".json":
            records = _validate_json(source)
        else:
            continue
        destination = fixture_target / source.name
        shutil.copy2(source, destination)
        files.append(
            {
                "path": destination.relative_to(target).as_posix(),
                "records": records,
                "sha256": _sha256(destination),
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "offline_only": True,
        "files": files,
        "submission_directory": "submissions",
    }
    (target / "training-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (submission_target / ".gitkeep").touch()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path(".training-workspace"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = build_workspace(args.target.resolve(), force=args.force)
    print(
        f"Training workspace ready: {args.target} "
        f"({len(manifest['files'])} fixture files, offline_only=true)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
