#!/usr/bin/env python3
"""Build paginated contact sheets for all rendered book diagrams."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.contact_sheet import build_contact_sheets  # noqa: E402


def main() -> int:
    pages, index_path = build_contact_sheets(
        ROOT / "assets/diagrams/manifest.json",
        ROOT / "output/visual-review/contact-sheets",
    )
    print(f"Built {len(pages)} contact sheets; index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
