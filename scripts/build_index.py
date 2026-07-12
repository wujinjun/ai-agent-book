#!/usr/bin/env python3
"""Regenerate glossary, references, and the cross-chapter index."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.publication_metadata import generate_supporting_pages  # noqa: E402


def main() -> int:
    outputs = generate_supporting_pages(ROOT, ROOT / "docs")
    for output in outputs.values():
        print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
