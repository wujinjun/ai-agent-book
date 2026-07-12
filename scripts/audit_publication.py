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

from ai_agent_book.publication_audit import audit_epub, audit_html, audit_pdf  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("format", choices=("html", "epub", "pdf", "all"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    issues = []
    if args.format in {"html", "all"}:
        html_path = args.path / "html" if args.format == "all" else args.path
        issues.extend(audit_html(html_path))
    if args.format in {"epub", "all"}:
        epub_path = (
            args.path / "epub/ai-agent-book-2026.epub" if args.format == "all" else args.path
        )
        issues.extend(audit_epub(epub_path))
    if args.format in {"pdf", "all"}:
        pdf_path = (
            args.path / "pdf/ai-agent-book-2026.pdf" if args.format == "all" else args.path
        )
        issues.extend(
            audit_pdf(
                pdf_path,
                min_pages=200,
                required_text=("AI Agent", "技术选型", "企业级 Agent 平台"),
            )
        )
    for issue in issues:
        print(f"{issue.path}: {issue.code}: {issue.detail}")
    if issues:
        print(f"Publication audit found {len(issues)} issue(s).", file=sys.stderr)
        return 1
    print("Publication audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
