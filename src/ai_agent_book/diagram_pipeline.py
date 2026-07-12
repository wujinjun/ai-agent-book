"""Portable Mermaid extraction and publication helpers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

MERMAID_FENCE = re.compile(
    r"^```mermaid[ \t]*\r?\n(?P<source>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
HEADING = re.compile(r"^#\s+(?P<title>.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class DiagramRecord:
    source_path: str
    index: int
    title: str
    alt: str
    diagram_id: str
    source: str
    source_asset: str
    svg_path: str
    png_path: str


def normalize_mermaid(source: str) -> str:
    """Normalize line endings and insignificant trailing whitespace for hashing."""

    lines = [line.rstrip() for line in source.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def extract_diagrams(source_path: Path, markdown: str) -> list[DiagramRecord]:
    """Extract Mermaid fences and assign content-addressed stable asset names."""

    heading = HEADING.search(markdown)
    chapter_title = (
        heading.group("title") if heading else source_path.stem.replace("-", " ").title()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", source_path.stem.lower()).strip("-") or "diagram"
    records: list[DiagramRecord] = []
    for index, match in enumerate(MERMAID_FENCE.finditer(markdown), start=1):
        normalized = normalize_mermaid(match.group("source"))
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
        diagram_id = f"{slug}-{digest}"
        title = f"{chapter_title} 图 {index}"
        records.append(
            DiagramRecord(
                source_path=source_path.as_posix(),
                index=index,
                title=title,
                alt=title,
                diagram_id=diagram_id,
                source=normalized,
                source_asset=f"source/{diagram_id}.mmd",
                svg_path=f"svg/{diagram_id}.svg",
                png_path=f"png/{diagram_id}.png",
            )
        )
    return records


def replace_mermaid(markdown: str, diagrams: list[DiagramRecord], asset_root: Path) -> str:
    """Replace Mermaid fences with EPUB-safe SVG/PNG picture elements."""

    iterator = iter(diagrams)

    def replacement(_: re.Match[str]) -> str:
        diagram = next(iterator)
        svg = (asset_root / diagram.svg_path).as_posix()
        png = (asset_root / diagram.png_path).as_posix()
        return (
            '<figure class="book-diagram">\n'
            "<picture>\n"
            f'<source type="image/svg+xml" srcset="{svg}">\n'
            f'<img src="{png}" alt="{diagram.alt}" loading="lazy">\n'
            "</picture>\n"
            f"<figcaption>{diagram.title}</figcaption>\n"
            "</figure>"
        )

    rendered = MERMAID_FENCE.sub(replacement, markdown)
    try:
        next(iterator)
    except StopIteration:
        return rendered
    raise ValueError("diagram list contains more records than Mermaid fences")


def write_manifest(diagrams: list[DiagramRecord], output: Path) -> Path:
    """Write a deterministic UTF-8 JSON manifest."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([asdict(item) for item in diagrams], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output
