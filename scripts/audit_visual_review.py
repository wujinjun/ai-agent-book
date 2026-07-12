#!/usr/bin/env python3
"""Audit the full-book visual review ledger."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.visual_review import audit_review_ledger  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group")
    args = parser.parse_args()
    ledger = ROOT / "notes/visual-review.yml"
    issues = audit_review_ledger(ROOT, ledger, group=args.group)
    for issue in issues:
        print(f"{issue.path}: {issue.section}: {issue.code}: {issue.detail}")
    if issues:
        print(f"Visual review found {len(issues)} issue(s).", file=sys.stderr)
        return 1
    print("Visual review passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
