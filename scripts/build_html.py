#!/usr/bin/env python3
"""Build the strict MkDocs HTML publication."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "mkdocs",
        "build",
        "--strict",
        "--site-dir",
        str(ROOT / "output/html"),
    ]
    try:
        completed = subprocess.run(command, cwd=ROOT, check=False, timeout=180)
    except subprocess.TimeoutExpired:
        print("MkDocs 构建超过 180 秒，已终止。", file=sys.stderr)
        return 124
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
