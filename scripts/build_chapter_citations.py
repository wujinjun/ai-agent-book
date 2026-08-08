#!/usr/bin/env python3
"""Insert deterministic, traceable citation blocks into all textbook chapters."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- chapter-citations:start -->"
END = "<!-- chapter-citations:end -->"
BLOCK_RE = re.compile(
    rf"\n## 本章引用\n{re.escape(START)}.*?{re.escape(END)}\n",
    re.DOTALL,
)


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_blocks(root: Path) -> dict[Path, str]:
    """Return updated chapter text keyed by path without writing files."""

    references = _load_yaml(root / "notes/references.yml")
    if not isinstance(references, list):
        raise ValueError("notes/references.yml must contain a list")
    reference_by_id = {str(item["id"]): item for item in references}
    if len(reference_by_id) != len(references):
        raise ValueError("duplicate reference id")

    manifest = _load_yaml(root / "notes/chapter-citations.yml")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("chapters"), dict):
        raise ValueError("chapter citation manifest is invalid")

    chapter_paths = sorted(root.glob("docs/part-*/ch*.md"))
    configured = {root / str(path) for path in manifest["chapters"]}
    if configured != set(chapter_paths):
        missing = sorted(
            path.relative_to(root).as_posix() for path in set(chapter_paths) - configured
        )
        extra = sorted(
            path.relative_to(root).as_posix() for path in configured - set(chapter_paths)
        )
        raise ValueError(f"chapter citation coverage mismatch: missing={missing}, extra={extra}")

    outputs: dict[Path, str] = {}
    for relative, citation_ids in manifest["chapters"].items():
        path = root / str(relative)
        if not isinstance(citation_ids, list) or len(citation_ids) < 3:
            raise ValueError(f"{relative}: at least three citations are required")
        unknown = [item for item in citation_ids if item not in reference_by_id]
        if unknown:
            raise ValueError(f"{relative}: unknown references {unknown}")

        lines = [
            "## 本章引用",
            START,
            "以下资料用于支撑本章的核心原理、工程边界与版本敏感说明：",
            "",
        ]
        for citation_id in citation_ids:
            item = reference_by_id[citation_id]
            lines.append(
                f"- [{citation_id}：{item['title']}](../references.md#ref-{citation_id})"
            )
        lines.extend([END, ""])
        block = "\n".join(lines)

        source = path.read_text(encoding="utf-8")
        if START in source or END in source:
            if source.count(START) != 1 or source.count(END) != 1:
                raise ValueError(f"{relative}: malformed generated citation block")
            updated = BLOCK_RE.sub("\n" + block, source)
        else:
            marker = "\n## 延伸阅读\n"
            if marker in source:
                updated = source.replace(marker, "\n" + block + marker, 1)
            else:
                updated = source.rstrip() + "\n\n" + block
        outputs[path] = updated
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if checked-in blocks are stale")
    args = parser.parse_args()

    stale: list[str] = []
    for path, expected in build_blocks(ROOT).items():
        current = path.read_text(encoding="utf-8")
        if current == expected:
            continue
        stale.append(path.relative_to(ROOT).as_posix())
        if not args.check:
            path.write_text(expected, encoding="utf-8")
    if args.check and stale:
        raise SystemExit("stale chapter citations: " + ", ".join(stale))
    action = "Checked" if args.check else "Updated"
    print(f"{action} {len(build_blocks(ROOT))} chapter citation blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
