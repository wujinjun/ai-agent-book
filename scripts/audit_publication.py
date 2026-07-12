#!/usr/bin/env python3
"""Command line publication audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.publication_audit import audit_html  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("format", choices=("html",))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    issues = audit_html(args.path)
    for issue in issues:
        print(f"{issue.path}: {issue.code}: {issue.detail}")
    if issues:
        print(f"Publication audit found {len(issues)} issue(s).", file=sys.stderr)
        return 1
    print("Publication audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
