"""Semantic and editorial audits for book diagrams."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from ai_agent_book.diagram_pipeline import MERMAID_FENCE, extract_diagrams, parse_mermaid_metadata

RELATIONS = {
    "flow",
    "state",
    "sequence",
    "architecture",
    "data",
    "decision",
    "hierarchy",
    "comparison",
    "concept",
    "security",
}
DISPOSITIONS = {"diagram", "table", "code-structure", "not-applicable"}


@dataclass(frozen=True, slots=True, order=True)
class VisualIssue:
    path: str
    section: str
    code: str
    detail: str


def audit_markdown_visuals(path: Path, markdown: str) -> list[VisualIssue]:
    """Check semantic metadata plus explanatory prose around Mermaid fences."""

    issues: list[VisualIssue] = []
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    for index, match in enumerate(MERMAID_FENCE.finditer(markdown), start=1):
        section = _section_before(markdown, match.start())
        metadata = parse_mermaid_metadata(match.group("source"))
        for key in ("id", "title", "alt"):
            if not metadata.get(key):
                issues.append(
                    VisualIssue(path.as_posix(), section, f"missing-{key}", f"diagram {index}")
                )
        semantic_id = metadata.get("id")
        title = metadata.get("title")
        alt = metadata.get("alt", "")
        if semantic_id:
            if semantic_id in seen_ids:
                issues.append(
                    VisualIssue(path.as_posix(), section, "duplicate-id", semantic_id)
                )
            seen_ids.add(semantic_id)
        if title:
            if title in seen_titles:
                issues.append(VisualIssue(path.as_posix(), section, "duplicate-title", title))
            seen_titles.add(title)
        if alt and len(re.sub(r"[\s，。；：、,.!?！？]", "", alt)) < 12:
            issues.append(VisualIssue(path.as_posix(), section, "short-alt", alt))
        if not _is_explanatory(_block_before(markdown, match.start())):
            issues.append(
                VisualIssue(path.as_posix(), section, "missing-introduction", f"diagram {index}")
            )
        if not _is_explanatory(_block_after(markdown, match.end())):
            issues.append(
                VisualIssue(path.as_posix(), section, "missing-explanation", f"diagram {index}")
            )
    return sorted(issues)


def audit_review_ledger(
    root: Path, ledger_path: Path, *, group: str | None = None
) -> list[VisualIssue]:
    """Cross-check the review ledger against Markdown content."""

    raw = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("files"), dict):
        raise ValueError("visual review ledger requires a files mapping")
    files = cast(dict[str, Any], raw["files"])
    issues: list[VisualIssue] = []
    for path_text, config_raw in sorted(files.items()):
        if not isinstance(config_raw, dict):
            raise ValueError(f"invalid visual ledger entry: {path_text}")
        config = cast(dict[str, Any], config_raw)
        if group is not None and config.get("group") != group:
            continue
        source_path = root / path_text
        if not source_path.is_file():
            issues.append(VisualIssue(path_text, "", "missing-file", path_text))
            continue
        markdown = source_path.read_text(encoding="utf-8")
        diagrams = extract_diagrams(Path(path_text), markdown)
        minimum = int(config.get("minimum_diagrams", 0))
        if len(diagrams) < minimum:
            issues.append(
                VisualIssue(path_text, "", "diagram-count", f"{len(diagrams)} < {minimum}")
            )
        semantic_ids = {diagram.semantic_id for diagram in diagrams}
        requirements = config.get("requirements", [])
        if not isinstance(requirements, list):
            raise ValueError(f"requirements must be a list: {path_text}")
        for requirement_raw in requirements:
            if not isinstance(requirement_raw, dict):
                raise ValueError(f"invalid requirement in {path_text}")
            requirement = cast(dict[str, Any], requirement_raw)
            relation = str(requirement.get("relation", ""))
            disposition = str(requirement.get("disposition", ""))
            requirement_id = str(requirement.get("id", ""))
            section = str(requirement.get("section", ""))
            if relation not in RELATIONS:
                issues.append(VisualIssue(path_text, section, "invalid-relation", relation))
            if disposition not in DISPOSITIONS:
                issues.append(
                    VisualIssue(path_text, section, "invalid-disposition", disposition)
                )
            if disposition == "diagram" and requirement_id not in semantic_ids:
                issues.append(
                    VisualIssue(path_text, section, "missing-diagram", requirement_id)
                )
            if disposition == "not-applicable" and not str(requirement.get("reason", "")).strip():
                issues.append(VisualIssue(path_text, section, "missing-reason", requirement_id))
        issues.extend(audit_markdown_visuals(Path(path_text), markdown))
    return sorted(issues)


def _section_before(markdown: str, position: int) -> str:
    headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", markdown[:position], re.MULTILINE)
    return headings[-1] if headings else ""


def _block_before(markdown: str, position: int) -> str:
    prefix = markdown[:position].rstrip()
    return re.split(r"\n\s*\n", prefix)[-1] if prefix else ""


def _block_after(markdown: str, position: int) -> str:
    suffix = markdown[position:].lstrip()
    return re.split(r"\n\s*\n", suffix, maxsplit=1)[0] if suffix else ""


def _is_explanatory(block: str) -> bool:
    stripped = block.strip()
    if not stripped or stripped.startswith(("#", "```", "|", "<")):
        return False
    return len(re.sub(r"\s", "", stripped)) >= 12
