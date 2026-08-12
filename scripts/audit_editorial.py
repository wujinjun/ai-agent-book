#!/usr/bin/env python3
"""Run deterministic Chinese editorial, citation, and rights checks."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REMOTE_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(https?://", re.IGNORECASE)
MARKETING_PATTERNS = ("业界领先", "颠覆性", "万能框架", "零成本上线")
AMBIGUOUS_PATTERNS = ("API接口", "截止目前", "最新的最新")
LAST_CHECKED_RE = re.compile(r"最后核对日期：(?P<date>\d{4}-\d{2}-\d{2})")
PUBLISHED_MARKDOWN_GLOBS = (
    "docs/**/*.md",
    "projects/**/*.md",
    "examples/**/*.md",
)


def _strip_code(source: str) -> str:
    parts = source.split("```")
    return "".join(parts[::2])


def _fence_issues(source: str) -> list[str]:
    """Return rendering issues for triple-backtick fenced blocks."""

    issues: list[str] = []
    inside = False
    for line_number, line in enumerate(source.splitlines(), 1):
        if not line.startswith("```"):
            continue
        if not inside and not line.removeprefix("```").strip():
            issues.append(f"unlabelled_code_fence:{line_number}")
        inside = not inside
    if inside:
        issues.append("unbalanced_code_fence")
    return issues


def audit(root: Path = ROOT) -> dict[str, Any]:
    """Return a structured report; an empty issues list means the gate passes."""

    chapters = sorted(root.glob("docs/part-*/ch*.md"))
    references = yaml.safe_load((root / "notes/references.yml").read_text(encoding="utf-8"))
    citation_manifest = yaml.safe_load(
        (root / "notes/chapter-citations.yml").read_text(encoding="utf-8")
    )
    reference_ids = {str(item["id"]) for item in references}
    issues: list[dict[str, str]] = []
    citation_count = 0

    for path in chapters:
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8")
        prose = _strip_code(source)
        if "最后核对日期" not in source:
            issues.append({"path": relative, "issue": "missing_last_checked_date"})
        checked = LAST_CHECKED_RE.search(source)
        if checked and date.fromisoformat(checked.group("date")) > date.today():
            issues.append({"path": relative, "issue": "future_last_checked_date"})
        if source.count("<!-- chapter-citations:start -->") != 1:
            issues.append({"path": relative, "issue": "missing_or_duplicate_citation_block"})
        configured = citation_manifest["chapters"].get(relative, [])
        if len(configured) < 3 or any(item not in reference_ids for item in configured):
            issues.append({"path": relative, "issue": "invalid_citation_manifest"})
        citation_count += len(configured)
        for issue in _fence_issues(source):
            issues.append({"path": relative, "issue": issue})
        if "\t" in source:
            issues.append({"path": relative, "issue": "tab_character"})
        if any(line.rstrip() != line for line in source.splitlines()):
            issues.append({"path": relative, "issue": "trailing_whitespace"})
        if REMOTE_IMAGE_RE.search(source):
            issues.append({"path": relative, "issue": "remote_image_without_local_provenance"})
        for pattern in (*MARKETING_PATTERNS, *AMBIGUOUS_PATTERNS):
            if pattern in prose:
                issues.append({"path": relative, "issue": f"editorial_pattern:{pattern}"})

    for path in (root / "docs").rglob("*.md"):
        if REMOTE_IMAGE_RE.search(path.read_text(encoding="utf-8")):
            relative = path.relative_to(root).as_posix()
            if not any(item["path"] == relative for item in issues):
                issues.append({"path": relative, "issue": "remote_image_without_local_provenance"})

    published_paths = {
        path
        for pattern in PUBLISHED_MARKDOWN_GLOBS
        for path in root.glob(pattern)
        if "superpowers" not in path.parts
    }
    chapter_set = set(chapters)
    for path in sorted(published_paths - chapter_set):
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        for issue in _fence_issues(source):
            issues.append({"path": relative, "issue": issue})

    return {
        "schema_version": 1,
        "checked": date.today().isoformat(),
        "chapters": len(chapters),
        "references": len(references),
        "chapter_citations": citation_count,
        "remote_images": 0 if not any("remote_image" in item["issue"] for item in issues) else 1,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
