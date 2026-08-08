#!/usr/bin/env python3
"""Audit GitHub-facing repository structure and tracked-file hygiene."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("README.md"),
    Path("CONTRIBUTING.md"),
    Path("COMPATIBILITY.md"),
    Path("SECURITY.md"),
    Path("CODE_OF_CONDUCT.md"),
    Path(".github/PULL_REQUEST_TEMPLATE.md"),
    Path(".github/ISSUE_TEMPLATE/bug_report.yml"),
    Path(".github/ISSUE_TEMPLATE/content_correction.yml"),
    Path(".github/ISSUE_TEMPLATE/framework_version.yml"),
)

FORBIDDEN_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
}

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^)\s]+)")


def tracked_paths(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [Path(item.decode()) for item in completed.stdout.split(b"\0") if item]


def audit_paths(paths: Iterable[Path]) -> list[str]:
    issues: list[str] = []
    for path in paths:
        parts = set(path.parts)
        if parts & FORBIDDEN_PARTS:
            issues.append(f"tracked cache or dependency directory: {path}")
        if path.parts and path.parts[0] in {"output", "tmp", "release-assets"}:
            issues.append(f"tracked generated artifact: {path}")
        if path.name == ".env":
            issues.append(f"tracked environment file: {path}")
    return issues


def audit_local_markdown_links(root: Path, paths: Iterable[Path]) -> list[str]:
    issues: list[str] = []
    for relative in paths:
        if relative.suffix.lower() != ".md":
            continue
        source = root / relative
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            raw_target = match.group("target").strip("<>")
            if raw_target.startswith(("#", "http://", "https://", "mailto:", "data:")):
                continue
            path_text = unquote(raw_target.partition("#")[0])
            if not path_text:
                continue
            target = (source.parent / path_text).resolve()
            if not target.exists():
                line = text.count("\n", 0, match.start()) + 1
                issues.append(f"broken local link: {relative}:{line} -> {raw_target}")
    return issues


def audit_repository(root: Path) -> list[str]:
    paths = tracked_paths(root)
    issues = audit_paths(paths)
    issues.extend(audit_local_markdown_links(root, paths))
    for required in REQUIRED_FILES:
        if not (root / required).is_file():
            issues.append(f"missing GitHub-facing file: {required}")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for marker in (
        "## 15 分钟 Quick Start",
        "## 十个项目展示",
        "docs/assets/readme-home.png",
        "GitHub Release v2026.8.0",
        "## 质量门禁",
    ):
        if marker not in readme:
            issues.append(f"README missing marker: {marker}")
    return issues


def main() -> int:
    issues = audit_repository(ROOT)
    for issue in issues:
        print(issue)
    if issues:
        print(f"Repository hygiene audit found {len(issues)} issue(s).", file=sys.stderr)
        return 1
    print("Repository hygiene audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
