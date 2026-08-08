#!/usr/bin/env python3
"""Scan tracked text files for high-confidence secret signatures."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class SecretFinding:
    path: Path
    line: int
    kind: str


PATTERNS = {
    "OpenAI-style key": re.compile(r"(?<![A-Za-z0-9_])(?:s" + r"k|r" + r"k)-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "AWS access key": re.compile(r"AKIA[A-Z0-9]{16}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
}

SKIPPED_PATHS = {
    Path("scripts/check_secrets.py"),
}


def scan_text(path: Path, text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append(SecretFinding(path=path, line=line_number, kind=kind))
    return findings


def tracked_paths(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [Path(item.decode()) for item in completed.stdout.split(b"\0") if item]


def scan_paths(root: Path, paths: Iterable[Path]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for relative in paths:
        if relative in SKIPPED_PATHS or relative.name.endswith(".env.example"):
            continue
        path = root / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        payload = path.read_bytes()
        if b"\0" in payload:
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(relative, text))
    return findings


def main() -> int:
    findings = scan_paths(ROOT, tracked_paths(ROOT))
    for finding in findings:
        print(f"{finding.path}:{finding.line}: possible {finding.kind}")
    if findings:
        print(f"Secret scan found {len(findings)} issue(s).", file=sys.stderr)
        return 1
    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
