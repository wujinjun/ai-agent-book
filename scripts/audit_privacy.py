#!/usr/bin/env python3
"""Scan tracked text for accidental personal paths, email addresses, and phone numbers."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class PrivacyFinding:
    path: Path
    line: int
    kind: str
    value: str


HOME_PATH = re.compile(r"(?P<value>/(?:Users|home)/(?P<user>[A-Za-z0-9._-]+)/)")
EMAIL = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"(?P<value>[A-Za-z0-9._%+-]+@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,}))"
)
CN_PHONE = re.compile(r"(?<!\d)(?P<value>1[3-9]\d{9})(?!\d)")

PLACEHOLDER_USERS = {"alice", "example", "user"}
PLACEHOLDER_DOMAINS = {"example.test", "example.invalid", "users.noreply.github.com"}
SKIPPED = {Path("scripts/audit_privacy.py")}


def tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [Path(item.decode()) for item in result.stdout.split(b"\0") if item]


def scan_text(path: Path, text: str) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in HOME_PATH.finditer(line):
            if match.group("user").lower() not in PLACEHOLDER_USERS:
                findings.append(
                    PrivacyFinding(path, line_number, "personal home path", match.group("value"))
                )
        for match in EMAIL.finditer(line):
            if match.group("domain").lower() not in PLACEHOLDER_DOMAINS:
                findings.append(
                    PrivacyFinding(path, line_number, "email address", match.group("value"))
                )
        for match in CN_PHONE.finditer(line):
            findings.append(PrivacyFinding(path, line_number, "phone number", match.group("value")))
    return findings


def scan_repository(root: Path = ROOT) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for relative in tracked_paths(root):
        if relative in SKIPPED:
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
    findings = scan_repository()
    for finding in findings:
        print(f"{finding.path}:{finding.line}: possible {finding.kind}: {finding.value}")
    if findings:
        print(f"Privacy audit found {len(findings)} issue(s).", file=sys.stderr)
        return 1
    print("Privacy audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
